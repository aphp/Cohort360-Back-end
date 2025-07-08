import json
import logging
from typing import Tuple, Optional

from django.utils import timezone

from admin_cohort.types import JobStatus
from cohort_job_server.base_operator import BaseCohortOperator
from cohort_job_server.query_executor_api import CohortCount, CohortCountAll, FeasibilityCount, query_executor_status_mapper,\
QueryExecutorClient, CohortQuery
from cohort_job_server.utils import _logger, JOB_STATUS, COUNT, MINIMUM, MAXIMUM, EXTRA, ERR_MESSAGE

_logger_err = logging.getLogger('django.request')


class CohortCounter(BaseCohortOperator):

    def launch_dated_measure_count(self,
                                   dm_id: str,
                                   json_query: str,
                                   auth_headers: dict,
                                   global_estimate: Optional[bool] = False,
                                   stage_details: Optional[str] = None,
                                   owner_username: Optional[str] = None) -> None:
        count_cls = global_estimate and CohortCountAll or CohortCount
        self.query_executor_requester.launch_request(count_cls(instance_id=dm_id,
                                                    json_query=json_query,
                                                    auth_headers=auth_headers,
                                                    owner_username=owner_username,
                                                    stage_details=stage_details
                                                    ))

    @staticmethod
    def translate_query(dm_id: str, json_query: str, auth_headers: dict) -> str:
        cohort_query = CohortQuery(instance_id=dm_id, **json.loads(json_query))
        cohort_count = CohortCount(instance_id=dm_id,
                                   json_query=json_query,
                                   auth_headers=auth_headers)
        return cohort_count.create_query_executor_request(cohort_query=cohort_query)

    @staticmethod
    def refresh_dated_measure_count(translated_query: str) -> None:
        QueryExecutorClient().count(input_payload=translated_query)

    def launch_feasibility_study_count(self,
                                       fs_id: str,
                                       json_query: str,
                                       auth_headers: dict,
                                       owner_username: Optional[str] = None) -> bool:
        response = self.query_executor_requester.launch_request(FeasibilityCount(instance_id=fs_id,
                                                                      json_query=json_query,
                                                                      auth_headers=auth_headers,
                                                                      owner_username=owner_username))
        return response.success

    def cancel_job(self, job_id: str) -> JobStatus:
        return self.query_executor_requester.cancel_job(job_id=job_id)

    @staticmethod
    def handle_patch_dated_measure(dm, data) -> None:
        _logger.info(f"DatedMeasure[{dm.uuid}] Received patch data: {data}")
        job_status = query_executor_status_mapper(data.get(JOB_STATUS))
        if not job_status:
            raise ValueError(f"Bad Request: Invalid job status: {data.get(JOB_STATUS)}")
        job_duration = str(timezone.now() - dm.created_at)
        if job_status == JobStatus.finished:
            data["measure"] = data.pop(COUNT, None)
            data["extra"] = data.pop(EXTRA, None)
            if dm.is_global:
                data.update({"measure_min": data.pop(MINIMUM, None),
                             "measure_max": data.pop(MAXIMUM, None)})
            _logger.info(f"DatedMeasure[{dm.uuid}] successfully updated from Query Executor")
        elif job_status == JobStatus.failed:
            data["request_job_fail_msg"] = data.pop(ERR_MESSAGE, None)
            _logger_err.error(f"DatedMeasure[{dm.uuid}] - Failed")
        else:
            _logger.info(f"DatedMeasure[{dm.uuid}] - Ended with status: {job_status}")
        data.update({"request_job_status": job_status,
                     "request_job_duration": job_duration})

    @staticmethod
    def handle_patch_feasibility_study(fs, data) -> Tuple[JobStatus, dict]:
        _logger.info(f"FeasibilityStudy[{fs.uuid}] Received patch data: {data}")
        job_status = data.get(JOB_STATUS, "")
        job_status = query_executor_status_mapper(job_status)
        counts_per_perimeter = {}
        try:
            if not job_status:
                raise ValueError(f"Bad Request: Invalid job status: {data.get(JOB_STATUS)}")
            if job_status == JobStatus.finished:
                data["total_count"] = int(data.pop(COUNT, 0))
                counts_per_perimeter = data.pop(EXTRA, {})
                if not counts_per_perimeter:
                    raise ValueError(f"Bad Request: Payload missing `{EXTRA}` key")
            elif job_status == JobStatus.failed:
                data["request_job_fail_msg"] = data.pop(ERR_MESSAGE, None)
                _logger_err.error(f"FeasibilityStudy[{fs.uuid}] - Failed")
            else:
                _logger.info(f"FeasibilityStudy[{fs.uuid}] - Ended with status: {job_status}")
        except ValueError as ve:
            _logger_err.error(f"FeasibilityStudy[{fs.uuid}] - Error on Query Executor callback - {ve}")
            raise ve
        data[JOB_STATUS] = job_status
        return job_status, counts_per_perimeter


