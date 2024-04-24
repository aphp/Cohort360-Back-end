import logging
import os
from typing import List

from django.utils import timezone
from rest_framework.exceptions import ValidationError

from admin_cohort.models import User
from admin_cohort.types import JobStatus
from cohort.models import CohortResult
from cohort.services.cohort_result import cohort_service
from exports.emails import check_email_address
from exports.models import ExportTable, Export, Datalab
from exports.services.rights_checker import rights_checker
from exports.tasks import launch_export_task
from exports.types import ExportType

env = os.environ

HIVE_DB_FOLDER = env.get('HIVE_DB_FOLDER')
EXPORT_CSV_PATH = env.get('EXPORT_CSV_PATH')
PERSON_TABLE = "person"

_logger = logging.getLogger('info')


class ExportService:

    def process_export_creation(self, data: dict, owner: User):
        self.do_pre_export_check(data=data, owner=owner)
        self.validate_tables_data(tables_data=data.get("export_tables", []))
        if data["output_format"] == ExportType.CSV:
            target_name = f"{owner.pk}_{timezone.now().strftime('%Y%m%d_%H%M%S%f')}"
            target_location = EXPORT_CSV_PATH
        else:
            datalab = Datalab.objects.get(pk=data["datalab"])
            target_name = f"{datalab.name}_{timezone.now().strftime('%Y%m%d_%H%M%S%f')}"
            target_location = HIVE_DB_FOLDER
        data.update({"owner": owner.pk,
                     "motivation": data.get('motivation', "").replace("\n", " -- "),
                     "target_name": target_name,
                     "target_location": target_location
                     })

    @staticmethod
    def do_pre_export_check(data: dict, owner: User) -> None:
        try:
            check_email_address(owner.email)
            export_tables = data.get("export_tables", [])
            source_cohorts_ids = [table.get("cohort_result_source") for table in export_tables]
            if data["output_format"] == ExportType.CSV:
                assert len(set(source_cohorts_ids)) == 1, "All export tables must have the same source cohort"
                if CohortResult.objects.get(pk__in=source_cohorts_ids).owner != owner:
                    raise ValidationError("The selected cohort does not belong to you")
                if not data.get('nominative'):
                    raise ValidationError("CSV exports in pseudonymized mode are not allowed")
            else:
                if not data.get('datalab'):
                    raise ValueError("Missing `datalab` for Jupyter export")
            rights_checker.check_owner_rights(owner=owner,
                                              output_format=data["output_format"],
                                              nominative=data["nominative"],
                                              source_cohorts_ids=source_cohorts_ids)
        except (ValidationError, KeyError, ValueError) as e:
            raise ValidationError(f"Pre export check failed, reason: {e}")
        data['request_job_status'] = JobStatus.validated

    @staticmethod
    def validate_tables_data(tables_data: List[dict]):
        source_cohort_id = None
        person_table_provided = False
        for export_table in tables_data:
            source_cohort_id = export_table.get('cohort_result_source')
            if source_cohort_id:
                try:
                    cohort_source = CohortResult.objects.get(pk=source_cohort_id)
                except CohortResult.DoesNotExist:
                    raise ValueError(f"Cohort `{source_cohort_id}` linked to table `{export_table.get('name')}` was not found")
                if cohort_source.request_job_status != JobStatus.finished:
                    raise ValueError(f"The provided cohort `{source_cohort_id}` did not finish successfully")

            if PERSON_TABLE in export_table.get("table_ids"):
                person_table_provided = True
                if not source_cohort_id:
                    raise ValueError(f"The `{PERSON_TABLE}` table can not be exported without a source cohort")

        if not (person_table_provided or source_cohort_id):
            raise ValueError(f"`{PERSON_TABLE}` table was not specified, must then provide source cohort for all tables")
        return True

    def create_tables(self, export_id: str, export_tables: List[dict], http_request) -> None:
        export = Export.objects.get(pk=export_id)
        create_cohort_subsets = False
        for export_table in export_tables:
            cohort_source, cohort_subset = None, None
            fhir_filter_id = export_table.get("fhir_filter")
            cohort_source_id = export_table.get("cohort_result_source")
            if cohort_source_id:
                cohort_source = CohortResult.objects.get(pk=cohort_source_id)
            for table_name in export_table.get("table_ids"):
                if not fhir_filter_id:
                    cohort_subset = cohort_source
                else:
                    create_cohort_subsets = True
                    cohort_subset = cohort_service.create_cohort_subset(owner_id=export.owner_id,
                                                                        table_name=table_name,
                                                                        fhir_filter_id=fhir_filter_id,
                                                                        source_cohort=cohort_source,
                                                                        http_request=http_request)
                ExportTable.objects.create(export=export,
                                           name=table_name,
                                           fhir_filter_id=fhir_filter_id,
                                           cohort_result_source=cohort_source,
                                           cohort_result_subset=cohort_subset)
        if not create_cohort_subsets:
            self.launch_export(export_id=export_id)

    def check_all_cohort_subsets_created(self, export: Export):
        for table in export.export_tables.filter(cohort_result_subset__isnull=False):
            if table.cohort_result_subset.request_job_status != JobStatus.finished:
                _logger.info(f"Export [{export.uuid}]: waiting for some cohort subsets to finish before launching export")
                return
        _logger.info(f"Export [{export.uuid}]: all cohort subsets were successfully created. Launching export.")
        self.launch_export(export_id=export.uuid)

    @staticmethod
    def launch_export(export_id: str):
        launch_export_task.delay(export_id)


export_service = ExportService()
