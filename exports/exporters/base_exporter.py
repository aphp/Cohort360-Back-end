import logging
import time
from datetime import datetime
from typing import Tuple

import requests
from django.utils import timezone
from requests import RequestException, HTTPError
from rest_framework.exceptions import ValidationError

from admin_cohort.models import User
from admin_cohort.types import JobStatus
from exports.emails import check_email_address, export_request_succeeded, push_email_notification, export_request_failed
from exports.models import ExportRequest, Export
from exports.exporters.infra_api import InfraAPI, JobResponse, JobStatusResponse
from exports.services.rights_checker import rights_checker
from exports.exporters.types import ExportType

_celery_logger = logging.getLogger('celery.app')
_logger_err = logging.getLogger('django.request')


class BaseExporter:

    def __init__(self):
        self.export_api = InfraAPI()
        self.service_name = None
        self.target_endpoint = None
        self.auth_token = None

    def validate(self, export_data: dict, owner: User, **kwargs) -> None:
        check_email_address(owner.email)
        try:
            rights_checker.check_owner_rights(owner=owner,
                                              output_format=export_data["output_format"],
                                              nominative=export_data["nominative"],
                                              source_cohorts_ids=[kwargs.get("cohort_id")])
        except ValidationError as e:
            raise ValidationError(f"Pre export check failed, reason: {e}")
        export_data['request_job_status'] = JobStatus.validated

    @staticmethod
    def complete_data(export_data: dict, owner: User, target_name: str, target_location: str) -> None:
        export_data.update({"owner": owner.pk,
                            "motivation": export_data.get('motivation', "").replace("\n", " -- "),
                            "target_name": f"{target_name}_{timezone.now().strftime('%Y%m%d_%H%M%S%f')}",
                            "target_location": target_location
                            })

    def handle(self, export: ExportRequest, params: dict) -> None:
        self.log_export_task(export.id, "Sending request to Infra API.")
        try:
            job_id = self.send_export(export=export, params=params)
            export.request_job_status = JobStatus.pending
            export.request_job_id = job_id
            export.save()
            self.log_export_task(export.id, f"Request sent, job {job_id} is now {JobStatus.pending}")
        except RequestException as e:
            self.mark_export_as_failed(export, e, f"Could not post export {export.id}")
            return

        try:
            self.wait_for_export_job(export)
        except HTTPError as e:
            self.mark_export_as_failed(export, e, f"Failure during export job {export.id}")
            return

        self.log_export_task(export.id, "Export job finished, now concluding.")

    def send_export(self, export: ExportRequest | Export, params: dict) -> str:
        self.log_export_task(export.pk, f"Asking to export for '{export.target_name}'")
        tables, user_for_pseudo = self.get_custom_params(export=export)
        params.update({"tables": tables,
                       "environment": self.export_api.target_environment,
                       "no_date_shift": export.nominative or not export.shift_dates,
                       "overwrite": False,
                       "user_for_pseudo": user_for_pseudo,
                       })
        url = f"{self.export_api.export_base_url}{self.target_endpoint}"
        response = requests.post(url=url, params=params, headers={'auth-token': self.auth_token})
        return JobResponse(response=response).task_id

    def get_custom_params(self, export: ExportRequest | Export) -> Tuple[str, str]:
        if isinstance(export, ExportRequest):
            required_table = self.export_api.required_table
            required_table = f"{required_table}:{export.cohort_id}:true"
            other_tables = ",".join(map(lambda t: f'{t.omop_table_name}::true', export.tables.exclude(omop_table_name=required_table)))
            tables = f"{required_table},{other_tables}"
            user_for_pseudo = not export.nominative and export.target_unix_account.name or None
        else:
            tables = ",".join(map(lambda t: f'{t.name}:{t.cohort_result_subset.fhir_group_id}:{t.respect_table_relationships}',
                                  export.export_tables.all()))
            user_for_pseudo = not export.nominative and export.datalab.name or None
        return tables, user_for_pseudo

    def wait_for_export_job(self, export: ExportRequest):
        errors_count = 0
        error_msg = ""
        status_resp = JobStatusResponse()

        while errors_count < 5 and not status_resp.job_ended:
            time.sleep(5)
            self.log_export_task(export.pk, f"Asking for status of job {export.request_job_id}.")
            try:
                status_resp = self.get_job_status(job_id=export.request_job_id)
                self.log_export_task(export.pk, f"Status received: {status_resp.job_status} - Err: {status_resp.err or ''}")
                if export.request_job_status != status_resp.job_status:
                    export.request_job_status = status_resp.job_status
                    export.save()
            except RequestException as e:
                self.log_export_task(export.pk, f"Status not received: {e}")
                errors_count += 1
                error_msg = str(e)

        if status_resp.job_status != JobStatus.finished:
            raise HTTPError(status_resp.err or "No 'err' value returned.")
        elif errors_count >= 5:
            raise HTTPError(f"5 times internal error during task -> {error_msg}")

    def get_job_status(self, job_id: str) -> JobStatusResponse:
        params = {"task_uuid": job_id,
                  "return_out_logs": True,
                  "return_err_logs": True
                  }
        job_status_url = f"{self.export_api.api_url}/{self.service_name}/task_status"
        response = requests.get(url=job_status_url, params=params, headers={'auth-token': self.auth_token})
        return JobStatusResponse(response)

    @staticmethod
    def finalize(export: ExportRequest | Export, start_time: datetime) -> None:
        export.request_job_duration = timezone.now() - start_time
        export.save()
        if isinstance(export, Export):
            cohort_id = export.output_format == ExportType.CSV and export.export_tables.first().cohort_result_source_id or None,
            selected_tables = export.export_tables.values_list("name", flat=True)
        else:
            cohort_id = export.cohort_id,
            selected_tables = export.tables.values_list("omop_table_name", flat=True)
        notification_data = dict(recipient_name=export.owner.display_name,
                                 recipient_email=export.owner.email,
                                 export_request_id=export.pk,
                                 cohort_id=cohort_id,
                                 cohort_name=export.cohort_name,
                                 output_format=export.output_format,
                                 database_name=export.target_name,
                                 selected_tables=selected_tables)
        push_email_notification(base_notification=export_request_succeeded, **notification_data)

    @staticmethod
    def mark_export_as_failed(export: ExportRequest, e: Exception, msg: str) -> None:
        err_msg = f"{msg}: {e}"
        _logger_err.error(f"[ExportTask] [ExportRequest: {export.pk}] {err_msg}")
        export.request_job_fail_msg = err_msg
        if export.request_job_status in [JobStatus.pending, JobStatus.validated, JobStatus.new]:
            export.request_job_status = JobStatus.failed
        try:
            notification_data = dict(recipient_name=export.owner.display_name,
                                     recipient_email=export.owner.email,
                                     cohort_id=export.cohort_id,
                                     cohort_name=export.cohort_name,
                                     error_message=export.request_job_fail_msg)
            push_email_notification(base_notification=export_request_failed, **notification_data)
        except OSError:
            _logger_err.error(f"[ExportTask] [ExportRequest: {export.pk}] Error sending export failure email notification")
        else:
            export.is_user_notified = True
        export.save()

    @staticmethod
    def log_export_task(export_id, msg):
        _celery_logger.info(f"[ExportTask][Export: {export_id}] {msg}")
