import logging
import os

from requests import RequestException

from exports.models import ExportRequest, Export
from exporters.base_exporter import BaseExporter
from exporters.enums import ExportTypes
from exporters.tasks import notify_export_received

_logger = logging.getLogger('django.request')


class HiveExporter(BaseExporter):

    def __init__(self):
        super().__init__()
        self.type = ExportTypes.HIVE
        self.target_location = os.environ.get('HIVE_DB_FOLDER')
        self.user = os.environ.get('HIVE_EXPORTER_USER')

    def handle_export(self, export: ExportRequest | Export) -> None:
        notify_export_received.delay(export.pk)
        self.prepare_db(export)
        super().handle(export=export, params={"database_name": export.target_name})
        self.conclude_export(export=export)

    def prepare_db(self, export: ExportRequest | Export) -> None:
        try:
            self.create_db(export=export)
            self.change_db_ownership(export=export, db_user=self.user)
        except RequestException as e:
            self.mark_export_as_failed(export, e, f"Error while preparing for export {export.id}")

    @staticmethod
    def get_db_location(export: ExportRequest | Export) -> str:
        return f"{export.target_full_path}.db"

    def create_db(self, export: ExportRequest | Export) -> None:
        db_location = self.get_db_location(export=export)
        self.log_export_task(export.id, f"Creating DB '{export.target_name}', location: {db_location}")
        try:
            job_id = self.export_api.create_db(name=export.target_name,
                                               location=db_location)
            self.log_export_task(export.id, f"Received Hive DB creation task_id: {job_id}")
            self.wait_for_job(job_id=job_id,
                              service=self.export_api.Services.HADOOP)
        except RequestException as e:
            _logger.error(f"Error on call to create Hive DB: {e}")
            raise e
        self.log_export_task(export.id, f"DB '{export.target_name}' created.")

    def change_db_ownership(self, export: ExportRequest | Export, db_user: str) -> None:
        try:
            self.export_api.change_db_ownership(location=self.get_db_location(export=export),
                                                db_user=db_user)
            self.log_export_task(export.id, f"`{db_user}` granted rights on DB `{export.target_name}`")
        except RequestException as e:
            raise RequestException(f"Error granting `{db_user}` rights on DB `{export.target_name}` - {e}")

    def conclude_export(self, export: ExportRequest | Export) -> None:
        try:
            db_user = export.target_unix_account.name
            self.change_db_ownership(export=export, db_user=db_user)
            self.log_export_task(export.id, f"DB '{export.target_name}' attributed to {db_user}. Conclusion finished.")
        except RequestException as e:
            self.mark_export_as_failed(export, e, f"Could not conclude export {export.id}")
