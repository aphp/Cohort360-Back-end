import json
import logging
import os
import zipfile
from io import BytesIO
from smtplib import SMTPException
from typing import Tuple, List

from celery import chain
from django.db.models import QuerySet
from django.template.loader import get_template

from accesses.models import Perimeter
from admin_cohort.settings import FRONT_URL
from admin_cohort.types import JobStatus, ServerError
from cohort.models import FeasibilityStudy
from cohort.job_server_api import job_server_status_mapper
from cohort.services.misc import get_authorization_header
from cohort.services.emails import send_email_notif_feasibility_report_ready, send_email_notif_error_feasibility_report
from cohort.tasks import feasibility_count_task, send_email_notification_task

env = os.environ

APHP_ID = int(env.get("TOP_HIERARCHY_CARE_SITE_ID"))
REPORTING_PERIMETER_TYPES = env.get("REPORTING_PERIMETER_TYPES").split(",")

FRONT_REQUEST_URL = f"{FRONT_URL}/cohort/new"

REPORT_FILE_NAME = "Rapport"

JOB_STATUS = "request_job_status"
COUNT = "count"
ERR_MESSAGE = "message"
EXTRA = "extra"


_logger = logging.getLogger('info')
_logger_err = logging.getLogger('django.request')


def bound_number(n: int) -> str:
    limit_10 = 10
    if 0 < n < limit_10:
        return f"< {limit_10}"
    elif n >= limit_10:
        bound = 10 * (n // 10)
        return f"{bound}-{bound+10}"
    else:
        return str(n)


class FeasibilityStudyService:

    @staticmethod
    def process_feasibility_study_request(fs_uuid: str, request):
        fs = FeasibilityStudy.objects.get(pk=fs_uuid)
        try:
            auth_headers = get_authorization_header(request)
            chain(*(feasibility_count_task.s(fs_uuid,
                                             fs.request_query_snapshot.serialized_query,
                                             auth_headers),
                    send_email_notification_task.s(fs_uuid)))()
        except Exception as e:
            fs.delete()
            raise ServerError("INTERNAL ERROR: Could not launch feasibility request") from e

    def process_patch_data(self, fs: FeasibilityStudy, data: dict) -> None:
        _logger.info(f"Received data to patch FeasibilityStudy: {data}")
        job_status = data.get(JOB_STATUS, "")
        job_status = job_server_status_mapper(job_status)

        try:
            if not job_status:
                raise ValueError(f"Bad Request: Invalid job status: {data.get(JOB_STATUS)}")
            if job_status == JobStatus.finished:
                data["total_count"] = int(data.pop(COUNT, 0))
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
        data[JOB_STATUS] = job_status

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
        request_name = fs.request_query_snapshot.request.name
        request_name = f"{' '.join(request_name.split()[:4])}..."
        return f"{REPORT_FILE_NAME}_{fs.created_at.strftime('%d-%m-%Y')}_{request_name}"

    def persist_feasibility_report(self, fs: FeasibilityStudy, counts_per_perimeter: dict):
        try:
            json_content, html_content = self.build_feasibility_report(counts_per_perimeter=counts_per_perimeter)
            snapshot = fs.request_query_snapshot
            context = {"request_name": snapshot.request.name,
                       "request_version": snapshot.version,
                       "request_date": snapshot.created_at,
                       "request_url": f"{FRONT_REQUEST_URL}/{snapshot.request.uuid}",
                       "html_content": html_content
                       }
            html_content = get_template("html/feasibility_report.html").render(context)
            contents = dict(json=json.dumps(json_content),
                            html=html_content)
            json_zip_bytes, html_zip_bytes = self.compress_report_contents(fs=fs, contents=contents)
            fs.report_json_content = json_zip_bytes
            fs.report_file = html_zip_bytes
            fs.save()
        except Exception as e:
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
            patients_count = bound_number(n=int(counts_per_perimeter.get(p_id, 0)))
            json_content[p_id] = patients_count
            html_content += f"""<li class="item">
                                <input type="checkbox" id="p{p_id}">
                                <div class="label-count">
                                    <label for="p{p_id}">{p.name}</label>
                                    <span id="count_p{p_id}">{patients_count}</span>
                                </div>
                             """
            children = p.children.filter(type_source_value__in=REPORTING_PERIMETER_TYPES)
            if children:
                content = self.generate_report_content(perimeters=children, counts_per_perimeter=counts_per_perimeter)
                json_content.update(content[0])
                html_content += content[1]
            html_content += '</li>'
        html_content += '</ul>'
        return json_content, html_content


feasibility_study_service = FeasibilityStudyService()
