import logging
from typing import Tuple

from django.utils import timezone

from admin_cohort.types import JobStatus
from cohort_job_server.base_operator import BaseCohortOperator
from cohort_job_server.sjs_api import CohortCount, CohortCountAll, FeasibilityCount, sjs_status_mapper
from cohort_job_server.utils import _logger, JOB_STATUS, COUNT, MINIMUM, MAXIMUM, EXTRA, ERR_MESSAGE

_logger_err = logging.getLogger('django.request')


class CohortCounter(BaseCohortOperator):

    def launch_dated_measure_count(self, dm_id: str, json_query: str, auth_headers: dict, global_estimate=False) -> None:
        count_cls = global_estimate and CohortCountAll or CohortCount
        self.sjs_requester.post_to_sjs(count_cls(instance_id=dm_id,
                                                 json_query=json_query,
                                                 auth_headers=auth_headers))

    def launch_feasibility_study_count(self, fs_id: str, json_query: str, auth_headers: dict) -> bool:
        response = self.sjs_requester.post_to_sjs(FeasibilityCount(instance_id=fs_id,
                                                                   json_query=json_query,
                                                                   auth_headers=auth_headers))
        return response.success

    def cancel_job(self, job_id: str) -> JobStatus:
        return self.sjs_requester.cancel_job(job_id=job_id)

    @staticmethod
    def handle_patch_dated_measure(dm, data) -> None:
        _logger.info(f"DatedMeasure[{dm.uuid}] Received patch data: {data}")
        job_status = sjs_status_mapper(data.get(JOB_STATUS))
        if not job_status:
            raise ValueError(f"Bad Request: Invalid job status: {data.get(JOB_STATUS)}")
        job_duration = str(timezone.now() - dm.created_at)
        if job_status == JobStatus.finished:
            if dm.is_global:
                data.update({"measure_min": data.pop(MINIMUM, None),
                             "measure_max": data.pop(MAXIMUM, None)})
            else:
                data["measure"] = data.pop(COUNT, None)
            _logger.info(f"DatedMeasure[{dm.uuid}] successfully updated from SJS")
        else:
            data["request_job_fail_msg"] = data.pop(ERR_MESSAGE, None)
            _logger_err.exception(f"DatedMeasure[{dm.uuid}] - Error on SJS callback")
        data.update({"request_job_status": job_status,
                     "request_job_duration": job_duration})

    @staticmethod
    def handle_patch_feasibility_study(fs, data) -> Tuple[JobStatus, dict]:
        _logger.info(f"FeasibilityStudy[{fs.uuid}] Received patch data: {data}")
        job_status = data.get(JOB_STATUS, "")
        job_status = sjs_status_mapper(job_status)
        counts_per_perimeter = {}
        try:
            if not job_status:
                raise ValueError(f"Bad Request: Invalid job status: {data.get(JOB_STATUS)}")
            if job_status == JobStatus.finished:
                data["total_count"] = int(data.pop(COUNT, 0))
                counts_per_perimeter = data.pop(EXTRA, {})
                if not counts_per_perimeter:
                    raise ValueError(f"Bad Request: Payload missing `{EXTRA}` key")
            else:
                data["request_job_fail_msg"] = data.pop(ERR_MESSAGE, None)
                _logger_err.exception(f"FeasibilityStudy[{fs.uuid}] - Error on SJS callback")
        except ValueError as ve:
            _logger_err.exception(f"FeasibilityStudy[{fs.uuid}] - Error on SJS callback - {ve}")
            raise ve
        data[JOB_STATUS] = job_status
        return job_status, counts_per_perimeter


