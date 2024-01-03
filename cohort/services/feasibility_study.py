import json
import logging
import os
import zipfile
from io import BytesIO
from smtplib import SMTPException
from typing import Tuple, List

from django.db.models import QuerySet
from django.template.loader import get_template

from accesses.models import Perimeter
from admin_cohort.types import JobStatus, ServerError
from cohort.models import FeasibilityStudy
from cohort.services.conf_cohort_job_api import fhir_to_job_status, get_authorization_header
from cohort.services.emails import send_email_notif_feasibility_report_requested, send_email_notif_feasibility_report_ready, \
    send_email_notif_error_feasibility_report
from cohort.tasks import get_feasibility_count_task

env = os.environ

APHP_ID = int(env.get("TOP_HIERARCHY_CARE_SITE_ID"))
REPORT_FILE_NAME = "rapport_etude_de_faisabilite"

JOB_STATUS = "request_job_status"
COUNT = "count"
ERR_MESSAGE = "message"
EXTRA = "extra"


_logger = logging.getLogger('info')
_logger_err = logging.getLogger('django.request')


class FeasibilityStudyService:

    def process_feasibility_study_request(self, fs_uuid: str, request):
        fs = FeasibilityStudy.objects.get(pk=fs_uuid)
        try:
            auth_headers = get_authorization_header(request)
            get_feasibility_count_task.delay(auth_headers,
                                             fs.request_query_snapshot.serialized_query,
                                             fs_uuid)
        except Exception as e:
            fs.delete()
            raise ServerError("INTERNAL ERROR: Could not launch feasibility request") from e
        self.send_email_feasibility_report_requested(fs=fs)

    def process_patch_data(self, fs: FeasibilityStudy, data: dict) -> None:
        _logger.info(f"Received data to patch FeasibilityStudy: {data}")
        job_status = data.get(JOB_STATUS, "")
        job_status = fhir_to_job_status().get(job_status.upper())

        try:
            if not job_status:
                raise ValueError(f"Bad Request: Invalid job status: {data.get(JOB_STATUS)}")
            if job_status == JobStatus.finished:
                data["total_count"] = data.pop(COUNT, None)
                counts_per_perimeter = data.pop(EXTRA, {})
                if not counts_per_perimeter:
                    raise ValueError(f"Bad Request: Payload missing `{EXTRA}` key")
                self.persist_feasibility_report(fs=fs, counts_per_perimeter=counts_per_perimeter)
                self.send_email_feasibility_report_ready(fs=fs)
            else:
                data["request_job_fail_msg"] = data.pop(ERR_MESSAGE, None)
                self.send_email_feasibility_report_error(fs=fs)
                _logger_err.exception(f"FeasibilityStudy [{fs.uuid}] - Error on SJS callback")
        except ValueError as ve:
            self.send_email_feasibility_report_error(fs=fs)
            _logger_err.exception(f"FeasibilityStudy [{fs.uuid}] - Error on SJS callback - {ve}")
            raise ve

    @staticmethod
    def send_email_feasibility_report_requested(fs: FeasibilityStudy) -> None:
        try:
            send_email_notif_feasibility_report_requested(request_name=fs.request_query_snapshot.request.name,
                                                          owner=fs.owner)
        except (ValueError, SMTPException) as e:
            _logger_err.exception(f"FeasibilityStudy [{fs.uuid}] - Couldn't send email to user "
                                  f"after requesting a feasibility report: {e}")

    @staticmethod
    def send_email_feasibility_report_ready(fs: FeasibilityStudy) -> None:
        try:
            send_email_notif_feasibility_report_ready(request_name=fs.request_query_snapshot.request.name,
                                                      owner=fs.owner,
                                                      fs_uuid=fs.uuid)
        except (ValueError, SMTPException) as e:
            _logger_err.exception(f"""FeasibilityStudy [{fs.uuid}] - Couldn't send "feasibility report ready" email to user: {e}""")

    @staticmethod
    def send_email_feasibility_report_error(fs: FeasibilityStudy) -> None:
        try:
            send_email_notif_error_feasibility_report(request_name=fs.request_query_snapshot.request.name,
                                                      owner=fs.owner)
        except (ValueError, SMTPException) as e:
            _logger_err.exception(f"""FeasibilityStudy [{fs.uuid}] - Couldn't send "feasibility report error" email to user: {e}""")

    @staticmethod
    def get_file_name(fs: FeasibilityStudy) -> str:
        return f"{REPORT_FILE_NAME}_{fs.created_at.strftime('%d-%m-%Y')}"

    def persist_feasibility_report(self, fs: FeasibilityStudy, counts_per_perimeter: dict):
        try:
            json_content, html_content = self.build_feasibility_report(counts_per_perimeter=counts_per_perimeter)
            html_content = get_template("html/feasibility_report.html").render({"html_content": html_content})
            contents = dict(json=json.dumps(json_content),
                            html=html_content)
            json_zip_bytes, html_zip_bytes = self.compress_report_contents(fs=fs, contents=contents)
            fs.report_json_content = json_zip_bytes
            fs.report_file = html_zip_bytes
            fs.save()
        except Exception as e :
            raise ValueError(f"Error saving feasibility report - {e}")

    def compress_report_contents(self, fs: FeasibilityStudy, contents: dict) -> List[bytes]:
        zipped_bytes = []
        for content_type, content in contents.items():
            in_memory_zip = BytesIO()
            file_name = self.get_file_name(fs=fs)
            with zipfile.ZipFile(in_memory_zip, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                zip_file.writestr(f"{file_name}.{content_type}", str(content))
            zipped_bytes.append(in_memory_zip.getvalue())
            in_memory_zip.close()
        return zipped_bytes

    def build_feasibility_report(self, counts_per_perimeter: dict) -> Tuple[dict, str]:
        root_perimeter = Perimeter.objects.filter(id=APHP_ID)
        return self.generate_report_content(perimeters=root_perimeter,
                                            counts_per_perimeter=counts_per_perimeter)

    def generate_report_content(self, perimeters: QuerySet, counts_per_perimeter: dict = None) -> Tuple[dict, str]:
        json_content = {}
        html_content = '<ul class="perimeters-tree">'

        for p in perimeters:
            p_id = p.cohort_id
            patients_count = counts_per_perimeter.get(p_id, 0)
            json_content[p_id] = patients_count
            html_content += f"""<li class="item">
                                <input type="checkbox" id="p{p_id}">
                                <div class="label-count">
                                    <label for="p{p_id}">{p.name}</label>
                                    <span id="count_p{p_id}" data-key="{patients_count}">{patients_count}</span>
                                </div>
                             """
            children = p.children.all()
            if children:
                content = self.generate_report_content(perimeters=children, counts_per_perimeter=counts_per_perimeter)
                json_content.update(content[0])
                html_content += content[1]
            html_content += '</li>'
        html_content += '</ul>'
        return json_content, html_content


feasibility_study_service = FeasibilityStudyService()
