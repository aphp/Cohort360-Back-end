import json
import logging
from smtplib import SMTPException

from django.utils import timezone

from accesses.models import Perimeter
from admin_cohort.types import JobStatus, ServerError
from cohort.models import DatedMeasure
from cohort.models.dated_measure import GLOBAL_DM_MODE
from cohort.services.conf_cohort_job_api import fhir_to_job_status, get_authorization_header
from cohort.services.emails import send_email_notif_feasibility_report_confirmed, send_email_notif_feasibility_report_ready
from cohort.tasks import get_count_task, cancel_previously_running_dm_jobs

JOB_STATUS = "request_job_status"
COUNT = "count"
MAXIMUM = "maximum"
MINIMUM = "minimum"
ERR_MESSAGE = "message"
EXTRA = "extra"


_logger = logging.getLogger('info')
_logger_err = logging.getLogger('django.request')


class DatedMeasureService:

    def process_dated_measure(self, dm_uuid: str, request):
        dm = DatedMeasure.objects.get(pk=dm_uuid)
        is_for_feasibility = json.loads(request.query_params.get("feasibility", "false"))
        if not is_for_feasibility:
            cancel_previously_running_dm_jobs.delay(dm_uuid)
        try:
            auth_headers = get_authorization_header(request)
            get_count_task.delay(auth_headers,
                                 dm.request_query_snapshot.serialized_query,
                                 dm_uuid,
                                 is_for_feasibility)
        except Exception as e:
            dm.delete()
            raise ServerError("INTERNAL ERROR: Could not launch count request") from e
        if is_for_feasibility:
            self.send_confirmation_email(dm=dm)

    def process_patch_data(self, dm: DatedMeasure, data: dict) -> None:
        _logger.info(f"Received data for DM patch: {data}")
        job_status = data.get(JOB_STATUS, "")
        job_status = fhir_to_job_status().get(job_status.upper())
        if not job_status:
            raise ValueError(f"Bad Request: Invalid job status: {data.get(JOB_STATUS)}")
        job_duration = str(timezone.now() - dm.created_at)

        if job_status == JobStatus.finished:
            count_per_perimeter = data.pop(EXTRA, {})
            if count_per_perimeter:
                self.send_email_report_ready(dm=dm, count_per_perimeter=count_per_perimeter)
            else:
                if dm.mode == GLOBAL_DM_MODE:
                    data.update({"measure_min": data.pop(MINIMUM, None),
                                 "measure_max": data.pop(MAXIMUM, None)
                                 })
                else:
                    data["measure"] = data.pop(COUNT, None)
                _logger.info(f"DatedMeasure [{dm.uuid}] successfully updated from SJS")
        else:
            data["request_job_fail_msg"] = data.pop(ERR_MESSAGE, None)
            _logger_err.exception(f"DatedMeasure [{dm.uuid}] - Error on SJS callback")

        data.update({"request_job_status": job_status,
                     "request_job_duration": job_duration
                     })

    @staticmethod
    def send_confirmation_email(dm: DatedMeasure) -> None:
        try:
            send_email_notif_feasibility_report_confirmed(request_name=dm.request_query_snapshot.request.name,
                                                          owner=dm.owner)
        except (ValueError, SMTPException) as e:
            _logger_err.exception(f"DatedMeasure [{dm.uuid}] - Couldn't send email to user "
                                  f"after requesting a feasibility report: {e}")

    @staticmethod
    def build_report_results(count_per_perimeter: dict) -> dict:
        report_results = {}
        for pid, count in count_per_perimeter.items():
            perimeter = Perimeter.objects.filter(cohort_id=pid).first()
            if not perimeter:
                continue
            report_results[perimeter.name] = count
        return report_results

    def send_email_report_ready(self, dm: DatedMeasure, count_per_perimeter: dict) -> None:
        report_results = self.build_report_results(count_per_perimeter)
        try:
            send_email_notif_feasibility_report_ready(request_name=dm.request_query_snapshot.request.name,
                                                      owner=dm.owner,
                                                      report_results=report_results)
        except (ValueError, SMTPException) as e:
            _logger_err.exception(f"""DatedMeasure [{dm.uuid}] - Couldn't send "feasibility report ready" email to user: {e}""")


dated_measure_service = DatedMeasureService()
