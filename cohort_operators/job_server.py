import json
import logging
from typing import Type, Callable

from pydantic import ValidationError
from requests import HTTPError
from rest_framework import status

from admin_cohort.settings import COHORT_LIMIT
from admin_cohort.types import JobStatus, MissingDataError
from cohort.models import CohortResult
from cohort_operators.misc import log_count_task, log_create_task, log_delete_task, log_count_all_task, log_feasibility_study_task
from cohort_operators.cohort_requests import CohortCreate, CohortCountAll, CohortCount, CohortCountFeasibility, AbstractCohortRequest
from cohort_operators import CohortQuery, SjsClient, JobServerResponse, job_server_status_mapper


_logger = logging.getLogger("info")
_logger_err = logging.getLogger("django.request")


LoggerType = Type[Callable[..., None]]


def cancel_job(job_id: str) -> JobStatus:
    if not job_id:
        raise MissingDataError("No job_id provided")
    log_delete_task(job_id, f"Step 1: Job {job_id} cancelled")
    resp = SjsClient().delete(job_id)
    result = resp.json()
    log_delete_task(job_id, f"Step 2: treat the response: {resp}, {result}")
    if resp.status_code == status.HTTP_403_FORBIDDEN:
        return JobStatus.finished

    if resp.status_code != status.HTTP_200_OK:
        raise HTTPError(f"Unexpected response code: {resp.status_code}: "
                        f"{result.get('error', 'no error')} - {result.get('message', 'no message')}")

    if 'status' not in result:
        raise MissingDataError(f"Missing `status` from response: {result}")

    s = job_server_status_mapper(result.get('status'))
    try:
        new_status = JobStatus(s)
    except ValueError as ve:
        raise ValueError(f"QUERY SERVER ERROR: status from response ({s}) is not expected. "
                         f"Values can be {[s.value for s in JobStatus]}") from ve

    if new_status not in [JobStatus.cancelled, JobStatus.finished]:
        raise MissingDataError(f"Status returned by FHIR is neither KILLED nor FINISHED -> {result.get('status')}")
    return new_status


def post_to_job_server(json_query: str, uuid: str, cohort_cls: AbstractCohortRequest, logger: LoggerType) -> JobServerResponse:
    try:
        logger(uuid, f"Step 1: Converting the json query: {json_query}")
        cohort_query = CohortQuery(cohortUuid=uuid, **json.loads(json_query))
        logger(uuid, f"Step 2: Sending request to Job Server: {cohort_query}")
        response = cohort_cls.action(cohort_query)
    except (TypeError, ValueError, ValidationError, HTTPError) as e:
        _logger_err.error(f"Error sending request to Job Server: {e}")
        job_server_resp = JobServerResponse(success=False, err_msg=str(e), status="ERROR")
    else:
        response = response.json()
        job_server_resp = JobServerResponse(success=True, **response)
    logger(uuid, f"Step 3: Received Job Server response {job_server_resp.__dict__}")
    obj_model = cohort_cls.model
    instance = obj_model.objects.get(pk=uuid)
    if job_server_resp.success:
        instance.request_job_id = job_server_resp.job_id
        if obj_model is CohortResult:
            count = instance.dated_measure.measure
            instance.request_job_status = count >= COHORT_LIMIT and JobStatus.long_pending or JobStatus.pending
    else:
        instance.request_job_status = job_server_resp.job_status
        instance.request_job_fail_msg = job_server_resp.err_msg
    instance.save()
    logger(uuid, f"Done: {job_server_resp.success and f'{obj_model.__name__} updated' or job_server_resp.err_msg}")
    return job_server_resp


def post_count_cohort(auth_headers: dict, json_query: str, dm_uuid: str, global_estimate: bool = False) -> None:
    count_cls, logger = global_estimate and (CohortCountAll, log_count_all_task) or (CohortCount, log_count_task)
    count_request = count_cls(auth_headers=auth_headers, sjs_client=SjsClient())
    post_to_job_server(json_query, dm_uuid, count_request, logger)


def post_create_cohort(auth_headers: dict, json_query: str, cr_uuid: str) -> None:
    cohort_request = CohortCreate(auth_headers=auth_headers, sjs_client=SjsClient())
    post_to_job_server(json_query, cr_uuid, cohort_request, log_create_task)


def post_count_for_feasibility(auth_headers: dict, json_query: str, fs_uuid: str) -> JobServerResponse:
    count_request = CohortCountFeasibility(auth_headers=auth_headers, sjs_client=SjsClient())
    return post_to_job_server(json_query, fs_uuid, count_request, log_feasibility_study_task)
