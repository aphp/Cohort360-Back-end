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
        found_source_cohorts = False
        for table in tables_data:
            if table.get("name") == PERSON_TABLE and not table.get("cohort_result_source"):
                raise ValueError("The `person` table can not be exported without a source cohort")
            if table.get("cohort_result_source"):
                found_source_cohorts = True
        if not found_source_cohorts:
            raise ValueError("No source cohort was provided. Must at least provide a source cohort for the `person` table")
        return True

    def create_tables(self, http_request, tables_data: List[dict], export: Export) -> None:
        create_cohort_subsets = False
        for td in tables_data:
            cohort_subset = None
            if td.get("cohort_result_source"):
                if not td.get("fhir_filter"):
                    cohort_subset = td.get("cohort_result_source")
                else:
                    create_cohort_subsets = True
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
        if not create_cohort_subsets:
            self.launch_export(export=export)

    def check_all_cohort_subsets_created(self, export: Export):
        for table in export.export_tables.filter(cohort_result_subset__isnull=False):
            if table.cohort_result_subset.request_job_status != JobStatus.finished:
                _logger.info(f"Export [{export.uuid}]: waiting for some cohort subsets to finish before launching export")
                return
        _logger.info(f"Export [{export.uuid}]: all cohort subsets were successfully created. Launching export.")
        self.launch_export(export=export)

    @staticmethod
    def launch_export(export: Export):
        launch_export_task.delay(export.uuid)


export_service = ExportService()
