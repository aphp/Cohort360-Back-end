import logging
from django.utils import timezone

from admin_cohort.types import JobStatus
from cohort.models import DatedMeasure
from cohort.models.dated_measure import GLOBAL_DM_MODE

from cohort.services.cohort_managers import CohortCountManager
from cohort_operators import job_server_status_mapper

JOB_STATUS = "request_job_status"
COUNT = "count"
MAXIMUM = "maximum"
MINIMUM = "minimum"
ERR_MESSAGE = "message"


_logger = logging.getLogger('info')
_logger_err = logging.getLogger('django.request')


class DatedMeasureService:

    @staticmethod
    def process_dated_measure(dm: DatedMeasure, request) -> None:
        CohortCountManager().handle_count(dm, request)

    @staticmethod
    def process_patch_data(dm: DatedMeasure, data: dict) -> None:
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
