import logging
from typing import List

from accesses.models import Perimeter
from accesses.services.accesses import accesses_service
from accesses.services.shared import DataRight
from admin_cohort.models import User
from admin_cohort.types import JobStatus
from cohort.models import CohortResult
from cohort.services.cohort_result import cohort_service
from exports.emails import check_email_address
from exports.models import ExportTable, Export
from exports.tasks import launch_export_task
from exports.types import ExportType

_logger = logging.getLogger('info')
PERSON_TABLE = "person"


class ExportService:

    def do_pre_export_check(self, validated_data: dict) -> None:
        check_email_address(validated_data["owner"].email)
        if validated_data["output_format"] == ExportType.CSV:
            self.validate_csv_export(validated_data)
        else:
            self.validate_hive_export(validated_data)

    def validate_csv_export(self, validated_data: dict):
        if not validated_data.get('nominative'):
            raise ValueError("CSV exports in pseudonymized mode are not allowed")

        export_tables = validated_data.get("export_tables", [])
        source_cohorts = [table.get("cohort_result_source") for table in export_tables]
        assert len(source_cohorts) == 1, "All export tables must have the same cohort source"

        if self.validate_owner_rights(owner=validated_data["owner"],
                                      output_format=validated_data["output_format"],
                                      nominative=validated_data["nominative"],
                                      source_cohorts=source_cohorts):
            validated_data['request_job_status'] = JobStatus.validated
        else:
            ...

    def validate_hive_export(self, validated_data: dict) -> None:
        target_datalab = validated_data.get('datalab')
        if not target_datalab:
            raise ValueError("Missing `datalab` for Jupyter export")

        owner = validated_data.get('owner')
        validated_data['request_job_status'] = JobStatus.validated
        validated_data['reviewer_fk'] = self.context.get('request').user
        if not conf_workspaces.is_user_bound_to_unix_account(owner, target_datalab.aphp_ldap_group_dn):
            raise ValueError(f"Le compte Unix destinataire ({target_datalab.pk}) "
                                  f"n'est pas lié à l'utilisateur voulu ({owner.pk})")
        self.validate_owner_rights(validated_data)

    def validate_owner_rights(self, owner: User, output_format:  str, nominative: bool, source_cohorts: List[CohortResult]):
        cohort_ids = []
        for cohort in source_cohorts:
            cohort_ids.extend(cohort.request_query_snapshot.perimeters_ids)
        perimeters_ids = Perimeter.objects.filter(cohort_id__in=cohort_ids).values_list('id', flat=True)
        data_rights = accesses_service.get_data_reading_rights(user=owner,
                                                               target_perimeters_ids=','.join(map(str, perimeters_ids)))
        self.check_rights_on_perimeters_for_exports(rights=data_rights,
                                                    export_type=output_format,
                                                    is_nominative=nominative)

    def check_rights_on_perimeters_for_exports(self, rights: List[DataRight], export_type: str, is_nominative: bool):
        assert export_type in [e.value for e in ExportType], "Wrong value for `export_type`"
        self.check_read_rights_on_perimeters(rights=rights, is_nominative=is_nominative)
        if export_type == ExportType.CSV:
            self.check_csv_export_rights_on_perimeters(rights=rights, is_nominative=is_nominative)
        else:
            self.check_jupyter_export_rights_on_perimeters(rights=rights, is_nominative=is_nominative)

    def check_read_rights_on_perimeters(self, rights: List[DataRight], is_nominative: bool):
        if is_nominative:
            wrong_perimeters = [r.perimeter_id for r in rights if not r.right_read_patient_nominative]
        else:
            wrong_perimeters = [r.perimeter_id for r in rights if not r.right_read_patient_pseudonymized]
        if wrong_perimeters:
            raise ValidationError(f"L'utilisateur n'a pas le droit de lecture {is_nominative and 'nominative' or 'pseudonymisée'} "
                                  f"sur les périmètres suivants: {wrong_perimeters}.")

    def check_csv_export_rights_on_perimeters(self, rights: List[DataRight], is_nominative: bool):
        if is_nominative:
            wrong_perimeters = [r.perimeter_id for r in rights if not r.right_export_csv_nominative]
        else:
            wrong_perimeters = [r.perimeter_id for r in rights if not r.right_export_csv_pseudonymized]
        if wrong_perimeters:
            raise ValidationError(f"L'utilisateur n'a pas le droit d'export CSV {is_nominative and 'nominatif' or 'pseudonymisé'} "
                                  f"sur les périmètres suivants: {wrong_perimeters}.")

    def check_jupyter_export_rights_on_perimeters(self, rights: List[DataRight], is_nominative: bool):
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
            cohort_source = table.get("cohort_result_source")
            if table.get("name") == PERSON_TABLE and not cohort_source:
                raise ValueError("The `person` table can not be exported without a source cohort")
            if cohort_source:
                if cohort_source.request_job_status != JobStatus.finished:
                    raise ValueError(f"The provided cohort `{cohort_source.uuid}` has not finished successfully")
                if cohort_source.owner != owner:
                    raise ValueError(f"The selected cohort for table `{table}` belongs to a different user")
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
