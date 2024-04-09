import logging
import os

from requests import RequestException

from admin_cohort.models import User
from exports.enums import ExportType
from exports.models import ExportRequest
from exports.exporters.base_exporter import BaseExporter
from workspaces.models import Account


_logger_err = logging.getLogger('django.request')


class HiveExporter(BaseExporter):

    def __init__(self):
        super().__init__()
        self.type = ExportType.HIVE
        self.db_folder = os.environ.get('HIVE_DB_FOLDER')
        self.user = os.environ.get('HIVE_EXPORTER_USER')

    def validate(self, export_data: dict, owner: User, **kwargs) -> None:
        super().validate(export_data=export_data, owner=owner, **kwargs)
        self.complete_data(export_data=export_data,
                           owner=owner,
                           target_name=Account.objects.get(pk=export_data["target_unix_account"]).name,
                           target_location=self.db_folder)

    def handle_export(self, export: ExportRequest) -> None:
        self.prepare_db(export)
        super().handle(export=export, params={"database_name": export.target_name})
        self.conclude_export(export=export)

    def prepare_db(self, export: ExportRequest) -> None:
        try:
            self.create_db(export=export)
            self.change_db_ownership(export=export, db_user=self.user)
        except RequestException as e:
            self.mark_export_as_failed(export, e, f"Error while preparing for export {export.id}")

    def create_db(self, export: ExportRequest) -> None:
        self.log_export_task(export.id, f"Creating DB '{export.target_name}', location: {export.target_full_path}")
        try:
            job_id = self.export_api.create_db(name=export.target_name,
                                               location=export.target_full_path)
            self.log_export_task(export.id, f"Received Hive DB creation task_id: {job_id}")
            self.wait_for_job(job_id=job_id,
                              service=self.export_api.Services.HADOOP)
        except RequestException as e:
            _logger_err.error(f"Error on call to create Hive DB: {e}")
            raise e
        self.log_export_task(export.id, f"DB '{export.target_name}' created.")

    def change_db_ownership(self, export: ExportRequest, db_user: str) -> None:
        try:
            self.export_api.change_db_ownership(location=export.target_full_path, db_user=db_user)
            self.log_export_task(export.id, f"`{db_user}` granted rights on DB `{export.target_name}`")
        except RequestException as e:
            raise RequestException(f"Error granting `{db_user}` rights on DB `{export.target_name}` - {e}")

    def conclude_export(self, export: ExportRequest) -> None:
        try:
            db_user = export.target_unix_account.name
            self.change_db_ownership(export=export, db_user=db_user)
            self.log_export_task(export.id, f"DB '{export.target_name}' attributed to {db_user}. Conclusion finished.")
        except RequestException as e:
            self.mark_export_as_failed(export, e, f"Could not conclude export {export.id}")
