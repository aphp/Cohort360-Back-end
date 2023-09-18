import logging
from typing import List

from admin_cohort.types import JobStatus
from cohort.services.cohort_result import cohort_service
from exports.models import ExportTable, Export
from exports.tasks import launch_export_task

_logger = logging.getLogger('info')
PERSON_TABLE = "person"


class ExportService:

    @staticmethod
    def validate_tables_data(tables_data: List[dict]):
        source_cohorts_count = 0
        for table in tables_data:
            if table.get("name") == PERSON_TABLE and not table.get("cohort_result_source"):
                raise ValueError("The `person` table can not be exported without a source cohort")
            if table.get("cohort_result_source"):
                source_cohorts_count += 1
        if not source_cohorts_count:
            raise ValueError("No source cohort was provided. Must at least provide a source cohort for the `person` table")
        return True

    @staticmethod
    def create_tables(http_request, tables_data: List[dict], export: Export) -> None:
        ExportService.validate_tables_data(tables_data=tables_data)
        count_cohort_subsets_to_create = 0
        for td in tables_data:
            cohort_subset = None
            if td.get("cohort_result_source"):
                if not td.get("fhir_filter"):
                    cohort_subset = td.get("cohort_result_source")
                else:
                    count_cohort_subsets_to_create += 1
                    cohort_subset = cohort_service.create_cohort_subset(owner_id=export.owner_id,
                                                                        table_name=td.get("name"),
                                                                        fhir_filter=td.get("fhir_filter"),
                                                                        source_cohort=td.get("cohort_result_source"),
                                                                        http_request=http_request)
            ExportTable.objects.create(export=export,
                                       name=td.get("name"),
                                       fhir_filter=td.get("fhir_filter"),
                                       cohort_result_source=td.get("cohort_result_source"),
                                       cohort_result_subset=cohort_subset)

        if not count_cohort_subsets_to_create:
            ExportService.launch_export(export=export)

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
