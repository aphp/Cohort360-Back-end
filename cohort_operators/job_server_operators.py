import logging
from typing import Tuple

from django.utils import timezone

from admin_cohort.types import JobStatus
from cohort.models import CohortResult
from cohort_operators.status_mapper import job_server_status_mapper
from cohort_operators.job_server import post_create_cohort, post_count_cohort, post_count_for_feasibility, cancel_job
from cohort_operators.tasks import notify_large_cohort_ready

JOB_STATUS = "request_job_status"
GROUP_ID = "group.id"
GROUP_COUNT = "group.count"
COUNT = "count"
MAXIMUM = "maximum"
MINIMUM = "minimum"
ERR_MESSAGE = "message"
EXTRA = "extra"


_logger = logging.getLogger('info')
_logger_err = logging.getLogger('django.request')


class CohortCountOperator:

    @staticmethod
    def launch_count(dm_id: str, json_query: str, auth_headers: dict, global_estimate=False) -> None:
        post_count_cohort(dm_id=dm_id,
                          json_query=json_query,
                          auth_headers=auth_headers,
                          global_estimate=global_estimate)

    @staticmethod
    def launch_feasibility_study_count(fs_id: str, json_query: str, auth_headers: dict) -> bool:
        resp = post_count_for_feasibility(fs_id=fs_id,
                                          json_query=json_query,
                                          auth_headers=auth_headers)
        return resp.success

    @staticmethod
    def cancel_job(job_id: str) -> None:
        cancel_job(job_id=job_id)

    @staticmethod
    def handle_patch_dated_measure(dm, data) -> None:
        _logger.info(f"DatedMeasure[{dm.uuid}] Received patch data: {data}")
        job_status = job_server_status_mapper(data.get(JOB_STATUS))
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
        job_status = job_server_status_mapper(job_status)
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


class CohortCreateOperator:

    @staticmethod
    def launch_cohort_creation(cohort_id: str, json_query: str, auth_headers: dict) -> None:
        post_create_cohort(cr_id=cohort_id,
                           json_query=json_query,
                           auth_headers=auth_headers)

    @staticmethod
    def handle_patch_cohort(cohort: CohortResult, data: dict) -> None:
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

    @staticmethod
    def handle_cohort_post_update(cohort: CohortResult, data: dict) -> None:
        job_server_data_keys = (JOB_STATUS, GROUP_ID, GROUP_COUNT)
        is_update_from_job_server = all(key in data for key in job_server_data_keys)
        is_update_from_etl = JOB_STATUS in data and len(data) == 1

        if is_update_from_job_server:
            _logger.info(f"Cohort[{cohort.uuid}] successfully updated from Job Server")
        if is_update_from_etl:
            notify_large_cohort_ready(cohort=cohort)
