from django.utils import timezone

from admin_cohort.types import JobStatus
from cohort.models import CohortResult
from cohort_job_server.base_operator import BaseCohortOperator
from cohort_job_server.sjs_api import sjs_status_mapper, CohortCreate
from cohort_job_server.tasks import notify_large_cohort_ready
from cohort_job_server.utils import _logger, JOB_STATUS, GROUP_ID, GROUP_COUNT, ERR_MESSAGE


class CohortCreator(BaseCohortOperator):

    def launch_cohort_creation(self, cohort_id: str, json_query: str, auth_headers: dict) -> None:
        self.sjs_requester.launch_request(CohortCreate(instance_id=cohort_id,
                                                       json_query=json_query,
                                                       auth_headers=auth_headers))

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
                    data["request_job_fail_msg"] = data.pop(ERR_MESSAGE, None)
            data['request_job_status'] = job_status
        if GROUP_ID in data:
            data["group_id"] = data.pop(GROUP_ID)
        if GROUP_COUNT in data:
            cohort.dated_measure.measure = data.pop(GROUP_COUNT)
            cohort.dated_measure.save()

    @staticmethod
    def handle_cohort_post_update(cohort: CohortResult, data: dict) -> None:
        sjs_data_keys = (JOB_STATUS, GROUP_ID, GROUP_COUNT)
        is_update_from_sjs = all(key in data for key in sjs_data_keys)
        is_update_from_etl = JOB_STATUS in data and len(data) == 1

        if is_update_from_sjs:
            _logger.info(f"Cohort[{cohort.uuid}] successfully updated from SJS")
        if is_update_from_etl:
            notify_large_cohort_ready.s(cohort_id=cohort.uuid).apply_async()