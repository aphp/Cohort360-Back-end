import json
import logging
import os
from smtplib import SMTPException
from typing import List

from django.db.models import Value, QuerySet
from django.utils import timezone

from accesses.models import Perimeter
from admin_cohort.types import JobStatus, ServerError
from cohort.models import DatedMeasure
from cohort.models.dated_measure import GLOBAL_DM_MODE
from cohort.models.feasibility_result import FeasibilityResult, FeasibilityResultCount
from cohort.services.conf_cohort_job_api import fhir_to_job_status, get_authorization_header
from cohort.services.emails import send_email_notif_feasibility_report_confirmed, send_email_notif_feasibility_report_ready
from cohort.tasks import get_count_task, cancel_previously_running_dm_jobs

env = os.environ

APHP_ID = int(env.get("TOP_HIERARCHY_CARE_SITE_ID"))

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
                self.save_counts(dm=dm, total_count=data.get(COUNT), count_per_perimeter=count_per_perimeter)
                self.send_email_report_ready(dm=dm)
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
    def save_counts(dm: DatedMeasure, total_count: int, count_per_perimeter: dict):
        fr = FeasibilityResult.objects.create(dated_measure=dm, total_count=total_count)
        feasibility_result_counts = []
        for e in count_per_perimeter:
            try:
                perimeter = Perimeter.objects.get(cohort_id=e.get('group_id', 0))
            except Perimeter.DoesNotExist:
                continue
            feasibility_result_counts.append(FeasibilityResultCount(feasibility_result=fr,
                                                                    perimeter_id=perimeter.id,
                                                                    count=e.get('count', 0)))
        FeasibilityResultCount.objects.bulk_create(feasibility_result_counts)

    @staticmethod
    def send_confirmation_email(dm: DatedMeasure) -> None:
        try:
            send_email_notif_feasibility_report_confirmed(request_name=dm.request_query_snapshot.request.name,
                                                          owner=dm.owner)
        except (ValueError, SMTPException) as e:
            _logger_err.exception(f"DatedMeasure [{dm.uuid}] - Couldn't send email to user "
                                  f"after requesting a feasibility report: {e}")

    @staticmethod
    def send_email_report_ready(dm: DatedMeasure) -> None:
        try:
            send_email_notif_feasibility_report_ready(request_name=dm.request_query_snapshot.request.name,
                                                      owner=dm.owner,
                                                      dm_uuid=dm.uuid)
        except (ValueError, SMTPException) as e:
            _logger_err.exception(f"""DatedMeasure [{dm.uuid}] - Couldn't send "feasibility report ready" email to user: {e}""")

    def build_feasibility_report(self, dm: DatedMeasure) -> str:
        result_counts = dm.feasibility_result.feasibility_result_counts.values('perimeter_id', 'count')
        aphp_perimeter = Perimeter.objects.filter(id=APHP_ID)
        html_content = self.generate_html_tree(perimeters=aphp_perimeter,
                                               result_counts=result_counts)
        return html_content

    @staticmethod
    def get_patients_count(perimeter_id: int, result_counts: List[dict] = None) -> int:
        for r in result_counts:
            if r['perimeter_id'] == perimeter_id:
                count = r['count']
                result_counts.remove(r)
                return count
        return 0

    def generate_html_tree(self, perimeters: QuerySet, result_counts: List[dict] = None) -> str:
        html_content = '<ul class="tree-list">'
        for p in perimeters:
            patients_count = self.get_patients_count(perimeter_id=p.id, result_counts=result_counts)
            html_content += f"""<li class="item">
                                <input type="checkbox" id="p{p.id}">
                                <label for="p{p.id}">{p.name}</label>
                                <strong id="count_p{p.id}">{patients_count}</strong>
                             """
            children = p.children.all()
            if children:
                html_content += self.generate_html_tree(perimeters=children, result_counts=result_counts)
            html_content += '</li>'
        html_content += '</ul>'
        return html_content


# def generate_html_tree(perimeters, level=1):
#     html_content = '<ul class="tree-list">'
#     for perimeter, perimeter_data in perimeters.items():
#         html_content += f"""<li class="item">
#                             <input type="checkbox" id="perimeter_{level}">
#                             <label for="perimeter_{level}">{perimeter}</label>
#                             <strong id="perimeter_{level}">{perimeter_data.get('count')}</strong>
#                          """
#         children = perimeter_data.get('children')
#         if children:
#             html_content += generate_html_tree(children, level + 1)
#         html_content += '</li>'
#     html_content += '</ul>'
#     return html_content


perimeters_tree2 = {
    'APHP': {
        'count': 42,
        'children': {
            'Perimeter 1': {
                'count': 23,
                'children': {
                    'Perimeter 1.1': {
                        'count': 17,
                        'children': {
                            'Perimeter 1.1.1': {
                                'count': 14,
                                'children': {}
                            },
                            'Perimeter 1.1.2': {
                                'count': 3,
                                'children': {}
                            }
                        }
                    },
                    'Perimeter 1.2': {
                        'count': 6,
                        'children': {}
                    }
                }
            },
            'Perimeter 2': {
                'count': 19,
                'children': {
                    'Perimeter 2.1': {
                        'count': 10,
                        'children': {}
                    },
                    'Perimeter 2.2': {
                        'count': 9,
                        'children': {
                            'Perimeter 2.2.1': {
                                'count': 7,
                                'children': {}
                            },
                            'Perimeter 2.2.2': {
                                'count': 2,
                                'children': {}
                            }
                        }
                    }
                }
            }
        }
    }
}


dated_measure_service = DatedMeasureService()
