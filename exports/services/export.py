import logging
from typing import List

from admin_cohort.types import JobStatus
from cohort.models import CohortResult
from cohort.services.cohort_result import cohort_service
from exports.models import ExportTable, Export
from exports.services.export_common import ExportBaseService
from exports.tasks import launch_export_task

_logger = logging.getLogger('info')


class ExportService(ExportBaseService):

    @staticmethod
    def create_tables(export: Export, tables: List[dict], **kwargs) -> bool:
        requires_cohort_subsets = False
        for table in tables:
            cohort_source, cohort_subset = None, None
            table_name = table.get("name")
            fhir_filter_id = table.get("fhir_filter")
            if table.get("cohort_result_source"):
                cohort_source = CohortResult.objects.get(pk=table.get("cohort_result_source"))
                if not fhir_filter_id:
                    cohort_subset = cohort_source
                else:
                    requires_cohort_subsets = True
                    cohort_subset = cohort_service.create_cohort_subset(owner_id=export.owner_id,
                                                                        table_name=table_name,
                                                                        fhir_filter_id=fhir_filter_id,
                                                                        source_cohort=cohort_source,
                                                                        http_request=kwargs.get("http_request"))
            ExportTable.objects.create(export=export,
                                       name=table_name,
                                       fhir_filter_id=fhir_filter_id,
                                       cohort_result_source=cohort_source,
                                       cohort_result_subset=cohort_subset)
        return requires_cohort_subsets

    @staticmethod
    def check_all_cohort_subsets_created(export: Export):
        for table in export.export_tables.filter(cohort_result_subset__isnull=False):
            if table.cohort_result_subset.request_job_status != JobStatus.finished:
                _logger.info(f"Export [{export.uuid}]: waiting for some cohort subsets to finish before launching export")
                return
        _logger.info(f"Export [{export.uuid}]: all cohort subsets were successfully created. Launching export.")
        launch_export_task.delay(export.pk)


export_service = ExportService()
