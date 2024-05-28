import logging

from django.utils import timezone

from admin_cohort.types import JobStatus
from cohort.models import CohortResult
from cohort.services.misc import get_authorization_header
from . import job_server_status_mapper
from .exceptions import ServerError
from .tasks import create_cohort_task


JOB_STATUS = "request_job_status"
GROUP_ID = "group.id"
GROUP_COUNT = "group.count"

_logger = logging.getLogger('info')


class CohortCreator:
    job_server_update_fields = (JOB_STATUS, GROUP_ID, GROUP_COUNT)
    etl_update_fields = (JOB_STATUS,)

    @staticmethod
    def launch_cohort_creation(cohort: CohortResult, request):
        try:
            create_cohort_task.s(auth_headers=get_authorization_header(request),
                                 json_query=cohort.request_query_snapshot.serialized_query,
                                 cohort_uuid=cohort.pk) \
                              .apply_async()

        except Exception as e:
            cohort.delete()
            raise ServerError("Could not launch cohort creation") from e

    @staticmethod
    def handle_patch_data(cohort: CohortResult, data: dict) -> None:
        _logger.info(f"Cohort[{cohort.uuid}]: Received patch data: {data}")
        if JOB_STATUS in data:
            job_status = job_server_status_mapper(data[JOB_STATUS])
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
