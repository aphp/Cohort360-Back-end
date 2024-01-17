import logging
import os
from typing import List

from django.utils import timezone
from rest_framework.exceptions import ValidationError

from accesses.models import Perimeter
from accesses.services.accesses import accesses_service
from accesses.services.shared import DataRight
from admin_cohort.models import User
from admin_cohort.types import JobStatus
from cohort.models import CohortResult
from cohort.services.cohort_result import cohort_service
from exports.emails import check_email_address
from exports.models import ExportTable, Export, Datalab
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
        self.validate_tables_data(tables_data=data.get("export_tables", []), owner=owner)
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

    def do_pre_export_check(self, data: dict, owner: User) -> None:
        try:
            check_email_address(owner.email)
            export_tables = data.get("export_tables", [])
            source_cohorts_ids = [table.get("cohort_result_source") for table in export_tables]
            if data["output_format"] == ExportType.CSV:
                if not data.get('nominative'):
                    raise ValidationError("CSV exports in pseudonymized mode are not allowed")
                assert len(source_cohorts_ids) == 1, "All export tables must have the same cohort source"
            else:
                if not data.get('datalab'):
                    raise ValueError("Missing `datalab` for Jupyter export")
            self.check_owner_rights(owner=owner,
                                    output_format=data["output_format"],
                                    nominative=data["nominative"],
                                    source_cohorts_ids=source_cohorts_ids)
        except (ValidationError, KeyError, ValueError) as e:
            raise ValidationError(f"Pre export check failed, reason: {e}")
        data['request_job_status'] = JobStatus.validated

    def check_owner_rights(self, owner: User, output_format:  str, nominative: bool, source_cohorts_ids: List[str]) -> None:
        cohort_ids = []
        for cohort in CohortResult.objects.filter(pk__in=source_cohorts_ids):
            cohort_ids.extend(cohort.request_query_snapshot.perimeters_ids)
        perimeters_ids = Perimeter.objects.filter(cohort_id__in=cohort_ids).values_list('id', flat=True)
        data_rights = accesses_service.get_data_reading_rights(user=owner,
                                                               target_perimeters_ids=','.join(map(str, perimeters_ids)))
        self.check_rights_on_perimeters_for_exports(rights=data_rights,
                                                    export_type=output_format,
                                                    is_nominative=nominative)

    def check_rights_on_perimeters_for_exports(self, rights: List[DataRight], export_type: str, is_nominative: bool):
        self.check_read_rights_on_perimeters(rights=rights, is_nominative=is_nominative)
        if export_type == ExportType.CSV:
            self.check_csv_export_rights_on_perimeters(rights=rights, is_nominative=is_nominative)
        else:
            self.check_jupyter_export_rights_on_perimeters(rights=rights, is_nominative=is_nominative)

    @staticmethod
    def check_read_rights_on_perimeters(rights: List[DataRight], is_nominative: bool):
        if is_nominative:
            wrong_perimeters = [r.perimeter_id for r in rights if not r.right_read_patient_nominative]
        else:
            wrong_perimeters = [r.perimeter_id for r in rights if not r.right_read_patient_pseudonymized]
        if wrong_perimeters:
            raise ValidationError(f"L'utilisateur n'a pas le droit de lecture {is_nominative and 'nominative' or 'pseudonymisée'} "
                                  f"sur les périmètres suivants: {wrong_perimeters}.")

    @staticmethod
    def check_csv_export_rights_on_perimeters(rights: List[DataRight], is_nominative: bool):
        if is_nominative:
            wrong_perimeters = [r.perimeter_id for r in rights if not r.right_export_csv_nominative]
        else:
            wrong_perimeters = [r.perimeter_id for r in rights if not r.right_export_csv_pseudonymized]
        if wrong_perimeters:
            raise ValidationError(f"L'utilisateur n'a pas le droit d'export CSV {is_nominative and 'nominatif' or 'pseudonymisé'} "
                                  f"sur les périmètres suivants: {wrong_perimeters}.")

    @staticmethod
    def check_jupyter_export_rights_on_perimeters(rights: List[DataRight], is_nominative: bool):
        if is_nominative:
            wrong_perimeters = [r.perimeter_id for r in rights if not r.right_export_jupyter_nominative]
        else:
            wrong_perimeters = [r.perimeter_id for r in rights if not r.right_export_jupyter_pseudonymized]
        if wrong_perimeters:
            raise ValidationError(f"L'utilisateur n'a pas le droit d'export Jupyter {is_nominative and 'nominatif' or 'pseudonymisé'} "
                                  f"sur les périmètres suivants: {wrong_perimeters}.")

    @staticmethod
    def validate_tables_data(tables_data: List[dict], owner: User):
        found_source_cohorts = False
        for table in tables_data:
            try:
                cohort_source = CohortResult.objects.get(pk=table.get("cohort_result_source"), owner=owner)
            except CohortResult.DoesNotExist:
                raise ValueError(f"Cohort with ID `{table.get('cohort_result_source')}` not found for table `{table.get('name')}`")

            if cohort_source.request_job_status != JobStatus.finished:
                raise ValueError(f"The provided cohort `{cohort_source.uuid}` did not finish successfully")
            found_source_cohorts = True
        if not found_source_cohorts:
            raise ValueError(f"No source cohort was provided. Must at least provide a source cohort for the `{PERSON_TABLE}` table")
        return True

    def create_tables(self, export_uuid: str, export_tables: List[dict], http_request) -> None:
        export = Export.objects.get(pk=export_uuid)
        create_cohort_subsets = False
        for table in export_tables:
            cohort_source, cohort_subset = None, None
            if table.get("cohort_result_source"):
                cohort_source = CohortResult.objects.get(pk=table.get("cohort_result_source"))
                if not table.get("fhir_filter"):
                    cohort_subset = cohort_source
                else:
                    create_cohort_subsets = True
                    cohort_subset = cohort_service.create_cohort_subset(owner_id=export.owner_id,
                                                                        table_name=table.get("name"),
                                                                        fhir_filter=table.get("fhir_filter"),
                                                                        source_cohort=table.get("cohort_result_source"),
                                                                        http_request=http_request)
            ExportTable.objects.create(export=export,
                                       name=table.get("name"),
                                       fhir_filter=table.get("fhir_filter"),
                                       cohort_result_source=cohort_source,
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
