import logging
import os
import time

import requests
from requests import RequestException, HTTPError

from admin_cohort.models import User
from admin_cohort.types import JobStatus
from exports.models import ExportRequest
from exports.exporters.base_exporter import BaseExporter
from exports.exporters.infra_api import JobResponse, JobStatusResponse, HiveDbOwnershipResponse
from workspaces.models import Account


_logger_err = logging.getLogger('django.request')


class HiveExporter(BaseExporter):

    def __init__(self):
        super().__init__()
        self.service_name = self.export_api.Services.HADOOP
        self.auth_token = self.export_api.hadoop_auth_token
        root_url = f"{self.export_api.api_url}/hadoop"
        self.new_db_url = f"{root_url}/hive/create_base_hive"
        self.chown_db_url = f"{root_url}/hdfs/chown_directory"
        self.target_endpoint = "/hive"
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
            self.create_hive_db(export=export)
            self.change_hive_db_ownership(export=export, db_user=self.user)
        except RequestException as e:
            self.mark_export_as_failed(export, e, f"Error while preparing for export {export.id}")

    def create_hive_db(self, export: ExportRequest) -> None:
        self.log_export_task(export.id, f"Creating DB '{export.target_name}', location: {export.target_full_path}")
        data = {"name": export.target_name,
                "location": export.target_full_path,
                "if_not_exists": False}
        try:
            response = requests.post(url=self.new_db_url, params=data, headers={'auth-token': self.auth_token})
            job_id = JobResponse(response=response).task_id
            self.log_export_task(export.id, f"Received Hive DB creation task_id: {job_id}")
            self.wait_for_hive_db_creation_job(job_id=job_id)
            self.log_export_task(export.id, f"DB '{export.target_name}' created.")
        except RequestException as e:
            _logger_err.error(f"Error on call to create Hive DB: {e}")
            raise e

    def wait_for_hive_db_creation_job(self, job_id) -> None:
        errors_count = 0
        status_resp = JobStatusResponse()

        while errors_count < 5 and not status_resp.job_ended:
            time.sleep(5)
            try:
                status_resp = self.get_job_status(job_id=job_id)
            except RequestException:
                errors_count += 1

        if status_resp.job_status != JobStatus.finished:
            raise HTTPError(f"Error on creating Hive DB {status_resp.err or 'No `err` value returned'}")
        elif errors_count >= 5:
            raise HTTPError("5 consecutive errors during Hive DB creation")

    def change_hive_db_ownership(self, export: ExportRequest, db_user: str) -> None:
        data = {"location": export.target_full_path,
                "uid": db_user,
                "gid": "hdfs",
                "recursive": True
                }
        try:
            response = requests.post(url=self.chown_db_url, params=data, headers={'auth-token': self.auth_token})
            response = HiveDbOwnershipResponse(response)
            if response.has_failed:
                raise RequestException(f"Granting rights did not succeed: {response.err}")
            self.log_export_task(export.id, f"`{db_user}` granted rights on DB `{export.target_name}`")
        except RequestException as e:
            raise RequestException(f"Error granting `{db_user}` rights on DB `{export.target_name}` - {e}")

    def conclude_export(self, export: ExportRequest) -> None:
        try:
            db_user = export.target_unix_account.name
            self.change_hive_db_ownership(export=export, db_user=db_user)
            self.log_export_task(export.id, f"DB '{export.target_name}' attributed to {db_user}. Conclusion finished.")
        except RequestException as e:
            self.mark_export_as_failed(export, e, f"Could not conclude export {export.id}")
