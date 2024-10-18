import logging
import time
from typing import List

from django.utils import timezone
from requests import RequestException

from admin_cohort.models import User
from admin_cohort.types import JobStatus
from cohort.models import CohortResult
from exports.emails import check_email_address
from exports.models import Export, Datalab, ExportTable
from exports.services.rights_checker import rights_checker
from exporters.infra_api import InfraAPI
from exporters.tasks import notify_export_received, notify_export_succeeded, notify_export_failed

_celery_logger = logging.getLogger('celery.app')
_logger = logging.getLogger('django.request')


class BaseExporter:

    def __init__(self):
        self.export_api = InfraAPI()
        self.type = None
        self.file_extension = None
        self.target_location = None

    def validate(self, export_data: dict, **kwargs) -> None:
        owner = kwargs["owner"]
        self.validate_tables_data(tables_data=export_data.get("export_tables", []))
        check_email_address(owner.email)
        self.check_user_rights(export_data=export_data, **kwargs)
        export_data['request_job_status'] = JobStatus.validated
        self.complete_data(export_data=export_data, owner=owner)


    def validate_tables_data(self, tables_data: List[dict]) -> bool:
        required_table = self.export_api.required_table
        base_cohort_provided = False
        required_table_provided = False
        for table_data in tables_data:
            source_cohort_id = table_data.get('cohort_result_source')

            if required_table in table_data.get("table_ids"):
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

    @staticmethod
    def check_user_rights(export_data: dict, **kwargs) -> None:
        rights_checker.check_owner_rights(owner=kwargs.get("owner"),
                                          output_format=export_data["output_format"],
                                          nominative=export_data["nominative"],
                                          source_cohorts_ids=kwargs.get("source_cohorts_ids"))

    def complete_data(self, export_data: dict, owner: User, **kwargs) -> None:
        target_name = kwargs.get("target_name")
        if not target_name:
            target_name = Datalab.objects.get(pk=export_data["datalab"]).name
        export_data.update({"owner": owner.pk,
                            "motivation": export_data.get('motivation', "").replace("\n", " -- "),
                            "target_name": f"{target_name}_{timezone.now().strftime('%Y%m%d_%H%M%S%f')}",
                            "target_location": self.target_location
                            })

    def handle_export(self, export: Export, **kwargs) -> None:
        params = kwargs.get("params", {})
        self.log_export_task(export.pk, "Sending request to Infra API.")
        start_time = timezone.now()
        try:
            job_id = self.send_export(export=export, params=params)
            if job_id is None:
                raise RequestException(f"Got an invalid Job ID: `{job_id}`")
            export.request_job_status = JobStatus.pending
            export.request_job_id = job_id
            export.save()
            self.log_export_task(export.pk, f"Request sent, job `{job_id}` is now {JobStatus.pending}")
            self.wait_for_export_job(export)
        except RequestException as e:
            self.mark_export_as_failed(export=export, reason=f"Error sending/tracking export: {e}")
            raise e
        export.request_job_duration = timezone.now() - start_time
        export.save()
        self.log_export_task(export.pk, "Export job finished")
        self.confirm_export_succeeded(export=export)

    def build_tables_input(self, export) -> str:
        required_table_name = self.export_api.required_table
        try:
            required_table = export.export_tables.get(name=required_table_name)
        except ExportTable.DoesNotExist:
            raise ValueError(f"Missing {required_table_name} table from export")

        linked_cohort = required_table.cohort_result_subset or required_table.cohort_result_source
        required_table = f"{required_table_name}:{linked_cohort.group_id}:{required_table.respect_table_relationships}"
        other_tables = ",".join(
            map(lambda t: f"{t.name}:{t.cohort_result_subset and t.cohort_result_subset.group_id or ''}:{t.respect_table_relationships}",
                export.export_tables.exclude(name=required_table_name)))
        return f"{required_table},{other_tables}"

    def send_export(self, export: Export, params: dict) -> str:
        self.log_export_task(export.pk, f"Asking to export for '{export.target_name}'")
        params.update({"export_type": self.type,
                       "tables": self.build_tables_input(export),
                       "no_date_shift": export.nominative or not export.shift_dates,
                       "user_for_pseudo": not export.nominative and export.datalab.name or None
                       })
        return self.export_api.launch_export(params=params)

    def wait_for_export_job(self, export: Export) -> None:
        job_status = self.wait_for_job(job_id=export.request_job_id,
                                       service=self.export_api.Services.BIG_DATA)
        export.request_job_status = job_status.value
        export.save()

    def wait_for_job(self, job_id: str, service: InfraAPI.Services) -> JobStatus:
        errors_count = 0
        job_status = JobStatus.pending

        while errors_count < 5 and not job_status.is_end_state:
            time.sleep(5)
            self.log_export_task("", f"Asking for status of job {job_id}.")
            try:
                job_status = self.export_api.get_job_status(job_id=job_id, service=service)
                self.log_export_task("", f"Received status: {job_status}")
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
        notify_export_failed.delay(export.pk, reason)

    @staticmethod
    def log_export_task(export_id, msg):
        _celery_logger.info(f"[ExportTask][Export {export_id}] {msg}")
