import logging
import os
from typing import List

from requests import RequestException

from cohort.models import CohortResult
from exports.models import ExportRequest, Export
from exporters.base_exporter import BaseExporter
from exporters.enums import ExportTypes

_logger = logging.getLogger('django.request')


class HiveExporter(BaseExporter):

    def __init__(self):
        super().__init__()
        self.type = ExportTypes.HIVE.value
        self.target_location = os.environ.get('HIVE_DB_FOLDER')
        self.user = os.environ.get('HIVE_EXPORTER_USER')

    def get_source_cohorts(self, export_data: dict) -> List[str]:
        using_new_export_models = self.using_new_export_models(export_data=export_data)
        if using_new_export_models:
            source_cohorts_ids = [t.get("cohort_result_source") for t in export_data.get("export_tables", [])]
        else:
            cohort = CohortResult.objects.get(fhir_group_id=export_data['cohort_id'])
            export_data['cohort'] = cohort.uuid
            source_cohorts_ids = [cohort.uuid]
        return source_cohorts_ids

    def validate(self, export_data: dict, **kwargs) -> None:
        kwargs["source_cohorts_ids"] = self.get_source_cohorts(export_data=export_data)
        super().validate(export_data=export_data, **kwargs)

    def handle_export(self, export: ExportRequest | Export, **kwargs) -> None:
        self.confirm_export_received(export=export)
        self.prepare_db(export)
        kwargs["params"] = {"database_name": export.target_name}
        super().handle_export(export=export, **kwargs)
        self.conclude_export(export=export)

    def prepare_db(self, export: ExportRequest | Export) -> None:
        try:
            self.create_db(export=export)
            self.change_db_ownership(export=export, db_user=self.user)
        except RequestException as e:
            self.mark_export_as_failed(export=export, reason=f"Error while preparing DB for export: {e}")

    @staticmethod
    def get_db_location(export: ExportRequest | Export) -> str:
        return f"{export.target_full_path}.db"

    def create_db(self, export: ExportRequest | Export) -> None:
        db_location = self.get_db_location(export=export)
        self.log_export_task(export.pk, f"Creating DB '{export.target_name}', location: {db_location}")
        try:
            job_id = self.export_api.create_db(name=export.target_name,
                                               location=db_location)
            self.log_export_task(export.pk, f"Received Hive DB creation task_id: {job_id}")
            self.wait_for_job(job_id=job_id,
                              service=self.export_api.Services.HADOOP)
        except RequestException as e:
            _logger.error(f"Error on call to create Hive DB: {e}")
            raise e
        self.log_export_task(export.pk, f"DB '{export.target_name}' created.")

    def change_db_ownership(self, export: ExportRequest | Export, db_user: str) -> None:
        try:
            self.export_api.change_db_ownership(location=self.get_db_location(export=export),
                                                db_user=db_user)
            self.log_export_task(export.pk, f"`{db_user}` granted rights on DB `{export.target_name}`")
        except RequestException as e:
            raise RequestException(f"Error granting `{db_user}` rights on DB `{export.target_name}` - {e}")

    def conclude_export(self, export: ExportRequest | Export) -> None:
        try:
            db_user = export.target_unix_account.name
        except AttributeError:
            db_user = export.datalab.name
        try:
            self.change_db_ownership(export=export, db_user=db_user)
            self.log_export_task(export.pk, f"DB '{export.target_name}' attributed to {db_user}. Conclusion finished.")
        except RequestException as e:
            self.mark_export_as_failed(export=export, reason=f"Could not conclude export: {e}")
