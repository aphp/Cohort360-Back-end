from django.utils import timezone

from admin_cohort.types import JobStatus
from cohort.models import CohortResult
from cohort_operators.job_server import post_create_cohort
from cohort_operators.sjs_api.status_mapper import sjs_status_mapper
from cohort_operators.tasks import notify_large_cohort_ready
from cohort_operators.misc import _logger, JOB_STATUS, GROUP_ID, GROUP_COUNT


class CohortCreator:

    @staticmethod
    def launch_cohort_creation(cohort_id: str, json_query: str, auth_headers: dict) -> None:
        post_create_cohort(cr_id=cohort_id,
                           json_query=json_query,
                           auth_headers=auth_headers)

    @staticmethod
    def handle_patch_cohort(cohort: CohortResult, data: dict) -> None:
        _logger.info(f"Cohort[{cohort.uuid}]: Received patch data: {data}")
        if JOB_STATUS in data:
            job_status = sjs_status_mapper(data[JOB_STATUS])
            if not job_status:
                raise ValueError(f"Bad Request: Invalid job status: {data.get(JOB_STATUS)}")
            if job_status in (JobStatus.finished, JobStatus.failed):
                data["request_job_duration"] = str(timezone.now() - cohort.created_at)
                if job_status == JobStatus.failed:
                    data["request_job_fail_msg"] = "Received a failed status from SJS"
            data['request_job_status'] = job_status
        if GROUP_ID in data:
            data["group_id"] = data.pop(GROUP_ID)
        if GROUP_COUNT in data:
            cohort.dated_measure.measure = data.pop(GROUP_COUNT)
            cohort.dated_measure.save()

    @staticmethod
    def handle_cohort_post_update(cohort: CohortResult, data: dict) -> None:
        job_server_data_keys = (JOB_STATUS, GROUP_ID, GROUP_COUNT)
        is_update_from_job_server = all(key in data for key in job_server_data_keys)
        is_update_from_etl = JOB_STATUS in data and len(data) == 1

        if is_update_from_job_server:
            _logger.info(f"Cohort[{cohort.uuid}] successfully updated from Job Server")
        if is_update_from_etl:
            notify_large_cohort_ready(cohort=cohort)
