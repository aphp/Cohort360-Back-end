import json
import logging
import os
import zipfile
from io import BytesIO
from typing import Tuple, List

from django.db.models import QuerySet
from django.template.loader import get_template

from accesses.models import Perimeter
from admin_cohort.settings import FRONT_URL
from admin_cohort.types import JobStatus
from cohort.models import FeasibilityStudy

from cohort.services.cohort_managers import CohortCounter
from cohort.tasks import send_email_feasibility_report_error, send_email_feasibility_report_ready

env = os.environ

REPORTING_PERIMETER_TYPES = env.get("REPORTING_PERIMETER_TYPES").split(",")

FRONT_REQUEST_URL = f"{FRONT_URL}/cohort/new"

REPORT_FILE_NAME = "Rapport"

JOB_STATUS = "request_job_status"
COUNT = "count"
ERR_MESSAGE = "message"
EXTRA = "extra"


_logger = logging.getLogger('info')
_logger_err = logging.getLogger('django.request')


class FeasibilityStudyService:

    @staticmethod
    def process_feasibility_study(fs: FeasibilityStudy, request) -> None:
        CohortCounter().handle_feasibility_study_count(fs, request)

    def handle_patch_data(self, fs: FeasibilityStudy, data: dict) -> None:
        try:
            job_status, counts_per_perimeter = CohortCounter().handle_patch_feasibility_study(fs, data)
        except ValueError as ve:
            send_email_feasibility_report_error(fs_id=fs.uuid)
            raise ve
        else:
            if job_status == JobStatus.finished:
                self.persist_feasibility_report(fs=fs, counts_per_perimeter=counts_per_perimeter)
                send_email_feasibility_report_ready(fs_id=fs.uuid)
            elif job_status == JobStatus.failed:
                send_email_feasibility_report_error(fs_id=fs.uuid)

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
        root_perimeter = Perimeter.objects.filter(parent__isnull=True, level=1)
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
            children = p.children.filter(type_source_value__in=REPORTING_PERIMETER_TYPES)
            if children:
                content = self.generate_report_content(perimeters=children, counts_per_perimeter=counts_per_perimeter)
                json_content.update(content[0])
                html_content += content[1]
            html_content += '</li>'
        html_content += '</ul>'
        return json_content, html_content


feasibility_study_service = FeasibilityStudyService()
