import logging
import time
from typing import List

from django.utils import timezone
from requests import RequestException

from admin_cohort.models import User
from admin_cohort.types import JobStatus
from exporters.apis.export_api import ExportAPI
from exporters.apis.hadoop_api import HadoopAPI
from exporters.enums import APIJobType, status_mapper
from exports.emails import check_email_address
from exports.models import Export, ExportTable
from exports.services.rights_checker import rights_checker
from exporters.tasks import notify_export_received, notify_export_succeeded, notify_export_failed

logger = logging.getLogger(__name__)


class BaseExporter:

    def __init__(self):
        self.export_api = ExportAPI()
        self.hadoop_api = HadoopAPI()
        self.type = None
        self.target_location = None

    def validate(self, export_data: dict, **kwargs) -> None:
        owner = kwargs["owner"]
        check_email_address(owner.email)
        self.check_user_rights(export_data=export_data, **kwargs)
        export_data['request_job_status'] = JobStatus.validated
        self.complete_data(export_data=export_data, owner=owner)


    @staticmethod
    def check_user_rights(export_data: dict, **kwargs) -> None:
        rights_checker.check_owner_rights(owner=kwargs.get("owner"),
                                          output_format=export_data["output_format"],
                                          nominative=export_data["nominative"],
                                          source_cohorts_ids=kwargs.get("source_cohorts_ids"))

    def complete_data(self, export_data: dict, owner: User, **kwargs) -> None:
        export_data.update({
            "owner": owner.pk,
            "motivation": export_data.get('motivation', "").replace("\n", " - "),
            "target_name": f"{kwargs.get('target_name')}_{timezone.now().strftime('%Y%m%d_%H%M%S%f')}",
            "target_location": self.target_location
        })

    def handle_export(self, export: Export, params: dict = None) -> None:
        self.log_export_task(export.pk, "Sending request to the Export API.")
        start_time = timezone.now()
        try:
            params = {**params, "overwrite": True}
            job_id = self.send_export(export=export, params=params)
            if job_id is None:
                raise RequestException(f"Got an invalid Job ID: `{job_id}`")
            export.request_job_status = JobStatus.pending
            export.request_job_id = job_id
            export.save()
            self.log_export_task(export.pk, f"Request sent, job `{job_id}` is now {JobStatus.pending}")
            self.wait_for_export_job(export)
        except RequestException as e:
            self.mark_export_as_failed(export=export, reason=f"Export terminated with an error: {e}")
            return
        export.request_job_duration = timezone.now() - start_time
        export.save()
        self.log_export_task(export.pk, "Export job finished")
        self.confirm_export_succeeded(export=export)

    def build_tables_input(self, export) -> List[dict[str, str]]:
        required_table_name = self.export_api.required_table
        try:
            required_table = export.export_tables.get(name=required_table_name)
            linked_cohort = required_table.cohort_result_subset or required_table.cohort_result_source
            required_table_data = {"tableName": required_table_name,
                                   "cohortId": linked_cohort.group_id,
                                   "relation": True
                                   }
            if required_table.columns:
                required_table_data["columnsToExport"] = required_table.columns
        except ExportTable.DoesNotExist:
            raise ValueError(f"Missing {required_table_name} table from export")

        other_tables = []
        for t in export.export_tables.exclude(name=required_table_name):
            t_data = {"tableName": t.name,
                      "relation": True
                      }
            if t.cohort_result_subset:
                t_data["cohortId"] = t.cohort_result_subset.group_id
            if t.columns:
                t_data["columnsToExport"] = t.columns
            other_tables.append(t_data)
        return [required_table_data] + other_tables

    def send_export(self, export: Export, params: dict) -> str:
        self.log_export_task(export.pk, f"Asking to export for '{export.target_name}'")
        params.update({"tablesToExport": self.build_tables_input(export),
                       "noDateShift": export.nominative or not export.shift_dates,
                       "disableTerminology": self.export_api.disable_data_translation,
                       })
        if not export.nominative:
            params["pseudo"] = export.datalab.name
        return self.export_api.launch_export(export_id=export.uuid, params=params)

    def wait_for_export_job(self, export: Export) -> None:
        job_status = self.wait_for_job(export=export, job_id=export.request_job_id, job_type=APIJobType.EXPORT)
        export.request_job_status = job_status.value
        export.save()

    def wait_for_job(self, export: Export, job_id: str, job_type: APIJobType) -> JobStatus:
        errors_count = 0
        job_status = JobStatus.pending

        while errors_count < 5 and not job_status.is_end_state:
            time.sleep(10)
            self.log_export_task(export.uuid, f"Asking for status of job `{job_id}`")
            target_api = (job_type == APIJobType.EXPORT and self.export_api
                          or job_type == APIJobType.HIVE_DB_CREATE and self.hadoop_api
                          or None)
            try:
                logs_response = target_api.get_export_logs(job_id=job_id)
                job_status = status_mapper.get(logs_response.get('task_status'), JobStatus.unknown)
                self.log_export_task(export.uuid, f"Job `{job_id}` is {job_status}")
                export.request_job_status = job_status.value
                export.save()
            except AttributeError as e:
                logging.error(f"No configured API found matching the job type `{job_type}`")
                raise e
            except RequestException:
                errors_count += 1

        if job_status != JobStatus.finished:
            raise RequestException(f"Job `{job_id}` ended with status `{job_status}`")
        return job_status

    @staticmethod
    def confirm_export_received(export: Export) -> None:
        notify_export_received.delay(export.pk)

    @staticmethod
    def confirm_export_succeeded(export: Export) -> None:
        notify_export_succeeded.delay(export.pk)

    @staticmethod
    def mark_export_as_failed(export: Export, reason: str) -> None:
        export.request_job_status = JobStatus.failed
        export.request_job_fail_msg = reason
        export.save()
        notify_export_failed.delay(export.pk, reason)

    @staticmethod
    def log_export_task(export_id, msg):
        logger.info(f"[Export {export_id}] {msg}")
