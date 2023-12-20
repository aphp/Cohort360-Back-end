import json
import logging
import os
import zipfile
from io import BytesIO
from smtplib import SMTPException

from django.db.models import QuerySet
from django.template.loader import get_template
from django.utils import timezone

from accesses.models import Perimeter
from admin_cohort.types import JobStatus, ServerError
from cohort.models import DatedMeasure
from cohort.models.dated_measure import GLOBAL_DM_MODE
from cohort.services.conf_cohort_job_api import fhir_to_job_status, get_authorization_header
from cohort.services.emails import send_email_notif_feasibility_report_requested, send_email_notif_feasibility_report_ready, \
    send_email_notif_error_feasibility_report
from cohort.tasks import get_count_task, cancel_previously_running_dm_jobs

env = os.environ

APHP_ID = int(env.get("TOP_HIERARCHY_CARE_SITE_ID"))
REPORT_FILE_NAME = "rapport_etude_de_faisabilite"

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
            self.send_email_feasibility_report_requested(dm=dm)

    def process_patch_data(self, dm: DatedMeasure, data: dict) -> None:
        _logger.info(f"Received data for DM patch: {data}")
        job_status = data.get(JOB_STATUS, "")
        job_status = fhir_to_job_status().get(job_status.upper())
        if not job_status:
            raise ValueError(f"Bad Request: Invalid job status: {data.get(JOB_STATUS)}")
        job_duration = str(timezone.now() - dm.created_at)

        if job_status == JobStatus.finished:
            if dm.mode == GLOBAL_DM_MODE:
                data.update({"measure_min": data.pop(MINIMUM, None),
                             "measure_max": data.pop(MAXIMUM, None)
                             })
            else:
                data["measure"] = data.pop(COUNT, None)
            _logger.info(f"DatedMeasure [{dm.uuid}] successfully updated from SJS")
            counts_per_perimeter = data.pop(EXTRA, {})
            if counts_per_perimeter:
                try:
                    self.persist_feasibility_report(dm=dm, counts_per_perimeter=counts_per_perimeter)
                except ValueError as e:
                    self.send_email_feasibility_report_error(dm=dm)
                    _logger_err.exception(f"DatedMeasure [{dm.uuid}] - Error saving feasibility report - {e}")
                self.send_email_feasibility_report_ready(dm=dm)
        else:
            data["request_job_fail_msg"] = data.pop(ERR_MESSAGE, None)
            self.send_email_feasibility_report_error(dm=dm)
            _logger_err.exception(f"DatedMeasure [{dm.uuid}] - Error on SJS callback")

        data.update({"request_job_status": job_status,
                     "request_job_duration": job_duration
                     })

    @staticmethod
    def send_email_feasibility_report_requested(dm: DatedMeasure) -> None:
        try:
            send_email_notif_feasibility_report_requested(request_name=dm.request_query_snapshot.request.name,
                                                          owner=dm.owner)
        except (ValueError, SMTPException) as e:
            _logger_err.exception(f"DatedMeasure [{dm.uuid}] - Couldn't send email to user "
                                  f"after requesting a feasibility report: {e}")

    @staticmethod
    def send_email_feasibility_report_ready(dm: DatedMeasure) -> None:
        try:
            send_email_notif_feasibility_report_ready(request_name=dm.request_query_snapshot.request.name,
                                                      owner=dm.owner,
                                                      dm_uuid=dm.uuid)
        except (ValueError, SMTPException) as e:
            _logger_err.exception(f"""DatedMeasure [{dm.uuid}] - Couldn't send "feasibility report ready" email to user: {e}""")

    @staticmethod
    def send_email_feasibility_report_error(dm: DatedMeasure) -> None:
        try:
            send_email_notif_error_feasibility_report(request_name=dm.request_query_snapshot.request.name,
                                                      owner=dm.owner)
        except (ValueError, SMTPException) as e:
            _logger_err.exception(f"""DatedMeasure [{dm.uuid}] - Couldn't send "feasibility report error" email to user: {e}""")

    @staticmethod
    def get_file_name(dm: DatedMeasure) -> str:
        return f"{REPORT_FILE_NAME}_{dm.created_at.strftime('%d-%m-%Y')}"

    def persist_feasibility_report(self, dm: DatedMeasure, counts_per_perimeter: dict) -> None:
        html_content = self.build_feasibility_report(counts_per_perimeter=counts_per_perimeter)
        html_report = get_template("html/feasibility_report.html").render({"html_content": html_content})
        in_memory_zip = BytesIO()
        file_name = self.get_file_name(dm=dm)
        with zipfile.ZipFile(in_memory_zip, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr(f"{file_name}.html", str.encode(html_report))
        zip_bytes = in_memory_zip.getvalue()
        in_memory_zip.close()
        dm.feasibility_report = zip_bytes
        dm.save()

    def build_feasibility_report(self, counts_per_perimeter: dict) -> str:
        root_perimeter = Perimeter.objects.filter(id=APHP_ID)
        return self.generate_html_tree(perimeters=root_perimeter,
                                       counts_per_perimeter=counts_per_perimeter)

    def generate_html_tree(self, perimeters: QuerySet, counts_per_perimeter: dict = None) -> str:
        html_content = '<ul class="perimeters-tree">'
        for p in perimeters:
            patients_count = counts_per_perimeter.get(p.cohort_id, 0)
            html_content += f"""<li class="item">
                                <input type="checkbox" id="p{p.cohort_id}">
                                <div class="label-count">
                                    <label for="p{p.cohort_id}">{p.name}</label>
                                    <span id="count_p{p.cohort_id}" data-key="{patients_count}">{patients_count}</span>
                                </div>
                             """
            children = p.children.all()
            if children:
                html_content += self.generate_html_tree(perimeters=children, counts_per_perimeter=counts_per_perimeter)
            html_content += '</li>'
        html_content += '</ul>'
        return html_content


dated_measure_service = DatedMeasureService()

# d_m = DatedMeasure.objects.get(pk='9714dbcb-d67f-4a41-a9d1-9978b2396120')
# html = dated_measure_service.build_feasibility_report(dm=d_m)
# with open("/home/hicham/dev/p3.html", 'w') as f:
#     f.write(html)

# counts_per_perimeter_1 = {group_id: count for (group_id, count) in
#                          [("47543", "10"), ("59559", "10"), ("109370", "10"), ("38297", "10"), ("73973", "10"),
#                           ("7735", "15"), ("59036", "15"), ("1034", "15"), ("215", "15"), ("71878", "15"), ("35876", "15"), ("57664", "25")]}
