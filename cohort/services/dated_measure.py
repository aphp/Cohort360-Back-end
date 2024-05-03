import logging
from django.utils import timezone

from admin_cohort.types import JobStatus, ServerError
from cohort.models import DatedMeasure
from cohort.models.dated_measure import GLOBAL_DM_MODE
from cohort.job_server_api import job_server_status_mapper
from cohort.services.misc import get_authorization_header
from cohort.tasks import count_cohort_task, cancel_previous_count_jobs

JOB_STATUS = "request_job_status"
COUNT = "count"
MAXIMUM = "maximum"
MINIMUM = "minimum"
ERR_MESSAGE = "message"


_logger = logging.getLogger('info')
_logger_err = logging.getLogger('django.request')


class DatedMeasureService:

    def process_dated_measure(self, dm_uuid: str, request):
        dm = DatedMeasure.objects.get(pk=dm_uuid)
        cancel_previous_count_jobs.delay(dm_uuid)
        try:
            auth_headers = get_authorization_header(request)
            count_cohort_task.s(auth_headers=auth_headers,
                                json_query=dm.request_query_snapshot.serialized_query,
                                dm_uuid=dm_uuid)\
                          .apply_async()
        except Exception as e:
            dm.delete()
            raise ServerError("INTERNAL ERROR: Could not launch count request") from e

    def process_patch_data(self, dm: DatedMeasure, data: dict) -> None:
        _logger.info(f"DatedMeasure [{dm.uuid}] Received patch data: {data}")
        job_status = job_server_status_mapper(data.get(JOB_STATUS))
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
        else:
            data["request_job_fail_msg"] = data.pop(ERR_MESSAGE, None)
            _logger_err.exception(f"DatedMeasure [{dm.uuid}] - Error on SJS callback")

        data.update({"request_job_status": job_status,
                     "request_job_duration": job_duration
                     })


dated_measure_service = DatedMeasureService()
