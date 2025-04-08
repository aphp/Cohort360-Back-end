import logging
import os
from typing import List

from requests import RequestException

from admin_cohort.models import User
from admin_cohort.types import JobStatus
from cohort.models import CohortResult
from exports.models import Export, Datalab
from exporters.exporters.base_exporter import BaseExporter
from exporters.enums import ExportTypes, APIJobType

_logger = logging.getLogger('django.request')


class HiveExporter(BaseExporter):

    def __init__(self):
        super().__init__()
        self.type = ExportTypes.HIVE.value
        self.file_extension = ".db"
        self.target_location = os.environ.get('HIVE_DB_FOLDER')
        self.user = os.environ.get('HIVE_EXPORTER_USER')

    def validate(self, export_data: dict, **kwargs) -> None:
        self.validate_tables_data(tables_data=export_data.get("export_tables", []))
        kwargs["source_cohorts_ids"] = [t.get("cohort_result_source")
                                        for t in export_data.get("export_tables", [])
                                        if t.get("cohort_result_source")]
        super().validate(export_data=export_data, **kwargs)

    def validate_tables_data(self, tables_data: List[dict]) -> bool:
        required_table = self.export_api.required_table
        base_cohort_provided = False
        required_table_provided = False
        for td in tables_data:
            source_cohort_id = td.get('cohort_result_source')

            if td.get("table_name", "") == required_table:
                required_table_provided = True
                if not source_cohort_id:
                    raise ValueError(f"The `{required_table}` table can not be exported without a source cohort")

            if source_cohort_id:
                if CohortResult.objects.filter(pk=source_cohort_id, request_job_status=JobStatus.finished).exists():
                    base_cohort_provided = True
                else:
                    raise ValueError(f"Cohort `{source_cohort_id}` not found or did not finish successfully")

        if not required_table_provided and not base_cohort_provided:
            raise ValueError(f"`{required_table}` table was not specified; must then provide source cohort for all tables")
        return True

    def complete_data(self, export_data: dict, owner: User, **kwargs) -> None:
        kwargs["target_name"] = Datalab.objects.get(pk=export_data["datalab"]).name
        super().complete_data(export_data=export_data, owner=owner, **kwargs)

    def handle_export(self, export: Export, params: dict = None) -> None:
        self.confirm_export_received(export=export)
        try:
            self.prepare_db(export)
        except RequestException as e:
            self.mark_export_as_failed(export=export, reason=f"Error while preparing DB for export: {e}")
        else:
            params = params or {"output": {"type": self.type,
                                           "databaseName": export.target_name
                                           }
                                }
            super().handle_export(export=export, params=params)
            self.conclude_export(export=export)

    def prepare_db(self, export: Export) -> None:
        self.create_db(export=export)
        self.change_db_ownership(export=export, db_user=self.user)

    def get_db_location(self, export: Export) -> str:
        return f"{export.target_full_path}{self.file_extension}"

    def create_db(self, export: Export) -> None:
        db_location = self.get_db_location(export=export)
        self.log_export_task(export.pk, f"Creating DB '{export.target_name}', location: {db_location}")
        try:
            job_id = self.infra_api.create_db(name=export.target_name,
                                              location=db_location)
            self.log_export_task(export.pk, f"Received Hive DB creation job_id: {job_id}")
            self.wait_for_job(export=export, job_id=job_id, job_type=APIJobType.HIVE_DB_CREATE)
        except RequestException as e:
            _logger.error(f"Error on call to create Hive DB: {e}")
            raise e
        self.log_export_task(export.pk, f"DB '{export.target_name}' created.")

    def change_db_ownership(self, export: Export, db_user: str) -> None:
        try:
            self.infra_api.change_db_ownership(location=self.get_db_location(export=export),
                                                db_user=db_user)
            self.log_export_task(export.pk, f"`{db_user}` granted rights on DB `{export.target_name}`")
        except RequestException as e:
            raise RequestException(f"Error granting `{db_user}` rights on DB `{export.target_name}` - {e}")

    def conclude_export(self, export: Export) -> None:
        db_user = export.datalab.name
        try:
            self.change_db_ownership(export=export, db_user=db_user)
            self.log_export_task(export.pk, f"Export concluded: DB '{export.target_name}' attributed to {db_user}.")
        except RequestException as e:
            self.mark_export_as_failed(export=export, reason=f"Could not conclude export: {e}")
