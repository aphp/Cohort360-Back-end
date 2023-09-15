import logging
from typing import List

from admin_cohort.types import JobStatus
from cohort.services.cohort_result import cohort_service
from exports.models import ExportTable, Export
from exports.tasks import launch_export_task

_logger = logging.getLogger('info')


class ExportService:

    @staticmethod
    def create_tables(http_request, tables_data: List[dict], export: Export):
        for td in tables_data:
            cohort_subset = None
            if td.get("cohort_id"):
                cohort_subset = cohort_service.create_cohort_subset(owner_id=export.owner_id,
                                                                    table_name=td.get("table_name"),
                                                                    cohort_id=td.get("cohort_id"),
                                                                    filter_id=td.get("filter_id"),
                                                                    http_request=http_request)
            ExportTable.objects.create(export=export,
                                       name=td.get("table_name"),
                                       fhir_filter_id=td.get("filter_id"),
                                       cohort_result_subset=cohort_subset,
                                       cohort_result_source_id=td.get("cohort_id"))

    @staticmethod
    def check_all_cohort_subsets_created(export: Export):
        for table in export.export_tables.filter(cohort_result_subset__isnull=False):
            if table.cohort_result_subset.request_job_status != JobStatus.finished:
                return
        _logger.info(f"Export [{export.uuid}]: all cohort subsets were successfully created. Launching export.")
        ExportService.launch_export(export=export)

    @staticmethod
    def launch_export(export: Export):
        launch_export_task.delay(export.uuid)


export_service = ExportService()
