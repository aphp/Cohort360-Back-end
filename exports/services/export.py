import logging
from typing import List, Dict

from celery import chain
from django.db.models.query_utils import Q
from django.http import StreamingHttpResponse
from django.core.exceptions import ImproperlyConfigured
from django.utils.module_loading import import_string
from requests.exceptions import RequestException
from rest_framework.exceptions import ValidationError

from admin_cohort.types import JobStatus
from cohort.models import CohortResult
from exports.apps import ExportsConfig
from exports.models import Export, ExportTable
from exports.services.export_operators import ExportDownloader
from exports.tasks import get_logs
from exports.export_tasks import (notify_export_received,
                                  create_cohort_subsets,
                                  relaunch_cohort_subsets,
                                  create_export_tables,
                                  await_cohort_subsets,
                                  prepare_export,
                                  send_export_request,
                                  track_export_job,
                                  finalize_export,
                                  notify_export_succeeded,
                                  mark_export_as_failed)


logger = logging.getLogger("info")

ExportTypes = ExportsConfig.ExportTypes
EXPORTERS = ExportsConfig.EXPORTERS


def load_available_exporters() -> dict:
    exporters = {}
    for exporter_conf in EXPORTERS:
        try:
            export_type, cls_path = exporter_conf["TYPE"], exporter_conf["EXPORTER_CLASS"]
            export_type = ExportTypes(export_type)
        except KeyError:
            raise ImproperlyConfigured("Missing `TYPE` or `EXPORTER_CLASS` key in exporter configuration")
        except ValueError as e:
            raise ImproperlyConfigured(f"Invalid export type: {e}")
        exporter = import_string(cls_path)
        if exporter:
            exporters[export_type] = exporter
        else:
            logger.warning(f"Improperly configured exporter `{cls_path}`")
    if not exporters:
        raise ImproperlyConfigured("No exporter is configured")
    return exporters


class ExportService:

    def __init__(self):
        self.exporters = load_available_exporters()

    def _get_exporter(self, export_type: str):
        try:
            return self.exporters[export_type]
        except KeyError:
            raise ImproperlyConfigured(f"Missing exporter configuration for type `{export_type}`")

    def validate(self, data: Dict, **kwargs) -> None:
        exporter = self._get_exporter(data.get("output_format"))
        try:
            exporter().validate(export_data=data, **kwargs)
        except Exception as e:
            raise ValidationError(f'Invalid export data: {e}')

    @staticmethod
    def proceed_with_export(export: Export, tables: List[Dict], auth_headers: Dict) -> bool:
        """ The tasks are chained in this specific order to reflect the export workflow.
            /!\ MODIFY WITH CAUTION /!\
            - Some tasks are called with .s() to take the output of the previous task as the 1st arg in their signature.
            - Others are called with .si() to ignore it
            - If a task fails, it passes the "failure reason" to the next tasks until it reaches the "mark_export_as_failed" task
        """
        source_cohorts_ids = [t.get("cohort_result_source") for t in tables if t.get("cohort_result_source")]
        assert source_cohorts_ids, "No `cohort_result_source` was provided for all tables"

        export_id = export.uuid
        main_cohort = CohortResult.objects.filter(uuid=source_cohorts_ids[0]).only("group_id", "name").first()

        tasks = chain(notify_export_received.s(export_id=export_id, cohort_id=main_cohort.group_id, cohort_name=main_cohort.name),
                      create_cohort_subsets.si(export_id=export_id, tables=tables, auth_headers=auth_headers),
                      create_export_tables.s(export_id=export_id, tables=tables),
                      await_cohort_subsets.s(export_id=export_id),
                      prepare_export.s(export_id=export_id),
                      send_export_request.s(export_id=export_id),
                      track_export_job.s(export_id=export_id),
                      finalize_export.s(export_id=export_id),
                      notify_export_succeeded.s(export_id=export_id),
                      mark_export_as_failed.s(export_id=export_id)
                      )
        tasks.apply_async()
        return True

    @staticmethod
    def download(export: Export) -> StreamingHttpResponse:
        return ExportDownloader().download(export=export)

    @staticmethod
    def retry(export: Export, auth_headers: Dict) -> bool:
        """
        For safety, restore related export tables if deleted
        - If the export has a valid value of 'request_job_id', it would have failed at the Export-API side, relaunch it as is
        - Otherwise, make sure cohort subsets were created or retry them as well.
        """
        export.request_job_status = JobStatus.new
        export.request_job_fail_msg = ""
        export.request_job_duration = ""
        export.save()

        export_id = export.uuid

        # restore deleted tables if any
        deleted_tables = ExportTable.deleted_objects.filter(export_id=export_id)
        if deleted_tables:
            logger.info(f"Export[{export_id}] Retry - Restoring deleted tables")
            deleted_tables.update(deleted=None)

        source_cohorts_ids = [t.cohort_result_source_id for t in export.export_tables.all()]
        assert source_cohorts_ids, "No `cohort_result_source` was provided for all tables"
        main_cohort = CohortResult.objects.filter(uuid=source_cohorts_ids[0]).only("group_id", "name").first()

        retry_tasks = [notify_export_received.s(export_id=export_id,
                                                cohort_id=main_cohort.group_id,
                                                cohort_name=main_cohort.name)]
        if export.request_job_id:
            logger.info(f"Export[{export_id}] Failed on the Export-API side")
        else:
            failed_cohort_subsets = export.export_tables.filter(Q(cohort_result_subset__isnull=False)
                                                                & ~Q(cohort_result_subset__request_job_status=JobStatus.finished))
            if failed_cohort_subsets.exists():
                # some cohort subsets failed. must try to re-launch them before proceeding to next steps
                # tables are already created as well as corresponding cohort subsets.
                # /!\ ensure cohort subsets are not deleted and restore them otherwise
                logger.info(f"Export[{export_id}] Retry - Found failed cohorts subsets. Will try to re-launch them")
                failed_cohort_subsets_ids = failed_cohort_subsets.values_list("uuid", flat=True)
                retry_tasks += [relaunch_cohort_subsets.si(export_id=export_id,
                                                           failed_cohort_subsets_ids=failed_cohort_subsets_ids,
                                                           auth_headers=auth_headers),
                                await_cohort_subsets.s(export_id=export_id),
                                ]
            else:
                logger.info(f"Export[{export_id}] Retry - No failed cohorts subsets found.")

        retry_tasks += [prepare_export.s(export_id=export_id),
                        send_export_request.s(export_id=export_id),
                        track_export_job.s(export_id=export_id),
                        finalize_export.s(export_id=export_id),
                        notify_export_succeeded.s(export_id=export_id),
                        mark_export_as_failed.s(export_id=export_id)
                        ]
        chain(*retry_tasks).apply_async()
        export.retried = True
        export.save()
        return True

    @staticmethod
    def get_execution_logs(export: Export, timeout: int = 30):
        try:
            result = get_logs.s(export_id=export.uuid).apply_async()
            return result.get(timeout=timeout)
        except (RequestException, TimeoutError) as e:
            logger.error(f"Export[{export.uuid}] Failed to retrieve logs: {e}")
            raise e


export_service = ExportService()
