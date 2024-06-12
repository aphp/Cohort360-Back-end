import logging
from typing import List

from django.http import StreamingHttpResponse
from rest_framework.exceptions import ValidationError

from admin_cohort.types import JobStatus
from cohort.models import CohortResult
from cohort.services.cohort_result import cohort_service
from exports.models import ExportTable, Export
from exports.services.export_operators import ExportDownloader, ExportManager
from exports.tasks import launch_export_task

_logger = logging.getLogger('info')


class ExportService:

    @staticmethod
    def validate_export_data(data: dict, **kwargs) -> None:
        try:
            ExportManager().validate(export_data=data, **kwargs)
        except Exception as e:
            raise ValidationError(f'Invalid export data: {e}')

    def proceed_with_export(self, export: Export, tables: List[dict], **kwargs) -> None:
        requires_cohort_subsets = self.create_tables(export, tables, **kwargs)
        if not requires_cohort_subsets:
            launch_export_task.delay(export.pk)

    @staticmethod
    def allow_create_sub_cohort_for_table(table_name: str) -> bool:
        return table_name not in ('imaging_series',
                                  'questionnaire__item',
                                  'questionnaireresponse__item',
                                  'questionnaireresponse__item__answer')

    def create_tables(self, export: Export, tables: List[dict], **kwargs) -> bool:
        requires_cohort_subsets = False
        for export_table in tables:
            fhir_filter_id = export_table.get("fhir_filter")
            cohort_source_id = export_table.get("cohort_result_source")
            cohort_source = cohort_source_id and CohortResult.objects.get(pk=cohort_source_id) or None
            for table_name in export_table.get("table_ids"):
                if self.allow_create_sub_cohort_for_table(table_name=table_name) and cohort_source and fhir_filter_id:
                    requires_cohort_subsets = True
                    cohort_subset = cohort_service.create_cohort_subset(owner_id=export.owner_id,
                                                                        table_name=table_name,
                                                                        fhir_filter_id=fhir_filter_id,
                                                                        source_cohort=cohort_source,
                                                                        http_request=kwargs.get("http_request"))
                else:
                    cohort_subset = None

                ExportTable.objects.create(export=export,
                                           name=table_name,
                                           fhir_filter_id=fhir_filter_id,
                                           cohort_result_source=cohort_source,
                                           cohort_result_subset=cohort_subset)
        return requires_cohort_subsets

    @staticmethod
    def check_all_cohort_subsets_created(export: Export):
        _logger.info(f"Export[{export.uuid}]: Checking if all cohort subsets were created...")
        for table in export.export_tables.filter(cohort_result_subset__isnull=False):
            cohort_subset_status = table.cohort_result_subset.request_job_status
            if cohort_subset_status == JobStatus.failed.value:
                failure_reason = "One or multiple cohort subsets has failed"
                _logger.info(f"Export[{export.uuid}]: Aborting export - {failure_reason}")
                ExportManager().mark_as_failed(export=export, reason=failure_reason)
                return
            elif cohort_subset_status != JobStatus.finished.value:
                _logger.info(f"Export[{export.uuid}]: waiting for cohort subsets to finish before launching export")
                return
        _logger.info(f"Export[{export.uuid}]: all cohort subsets were successfully created. Launching export.")
        launch_export_task.delay(export.pk)

    @staticmethod
    def download(export: Export) -> StreamingHttpResponse:
        return ExportDownloader().download(export=export)


export_service = ExportService()
