import json
import logging
import os
from datetime import datetime
from typing import Tuple, Dict, Type, TypeVar, Callable

import requests
from pydantic import ValidationError
from requests import Response, HTTPError
from rest_framework import status
from rest_framework.request import Request

from admin_cohort.middleware.request_trace_id_middleware import add_trace_id
from admin_cohort.settings import COHORT_LIMIT
from admin_cohort.types import JobStatus, MissingDataError
from cohort.crb import CohortQuery, CohortCreate, CohortCountAll, CohortCount, AbstractCohortRequest, SjsClient
from cohort.crb.cohort_requests.count_feasibility import CohortCountFeasibility
from cohort.models import CohortResult
from cohort.services.misc import log_count_task, log_create_task, log_delete_task, log_count_all_task, log_feasibility_study_task

env = os.environ

COHORT_REQUEST_BUILDER_URL = os.environ.get('COHORT_REQUEST_BUILDER_URL')
JOBS_API = f"{COHORT_REQUEST_BUILDER_URL}/jobs"
CREATE_COHORT_API = f"{COHORT_REQUEST_BUILDER_URL}/create"
COUNT_API = f"{COHORT_REQUEST_BUILDER_URL}/count"
GLOBAL_COUNT_API = f"{COHORT_REQUEST_BUILDER_URL}/countAll"
VALIDATE_QUERY_API = f"{COHORT_REQUEST_BUILDER_URL}/validate"
FHIR_CANCEL_ACTION = "cancel"

_logger = logging.getLogger("info")
_logger_err = logging.getLogger("django.request")
_celery_logger = logging.getLogger("django.request")


def parse_date(d):
    possible_formats = ['%Y-%m-%d %H:%M:%S.%f',
                        '%Y-%m-%dT%H:%M:%S.%fZ',
                        '%a, %d %b %Y %H:%M:%S',
                        '%a, %d %b %Y %H:%M:%S %z (%Z)',
                        '%a, %d %b %Y %H:%M:%S %Z',
                        '%a, %d %b %Y %H:%M:%S %z',
                        '%d %b %Y %H:%M:%S %z',
                        '%a, %d %b %Y %H:%M %z',
                        '%a, %d %b %y %H:%M:%S %Z',
                        '%d %b %Y %H:%M:%S %Z']
    for f in possible_formats:
        try:
            return datetime.strptime(d, f)
        except ValueError:
            pass
    raise ValueError(f"Unsupported date format {d}")


def fhir_to_job_status() -> Dict[str, JobStatus]:
    return {"KILLED": JobStatus.cancelled,
            "FINISHED": JobStatus.finished,
            "RUNNING": JobStatus.started,
            "STARTED": JobStatus.started,
            "ERROR": JobStatus.failed,
            "UNKNOWN": JobStatus.unknown,
            "PENDING": JobStatus.pending,
            "LONG_PENDING": JobStatus.long_pending
            }


def get_authorization_header(request: Request) -> dict:
    headers = {"Authorization": f"Bearer {request.META.get('HTTP_AUTHORIZATION')}",
               "authorizationMethod": request.META.get('HTTP_AUTHORIZATIONMETHOD')
               }
    headers = add_trace_id(headers)
    return headers


class JobServerResponse:
    def __init__(self, success: bool = False, err_msg: str = "", **kwargs):
        self.success = success
        self.err_msg = err_msg
        job_status = kwargs.get('status', '')
        self.job_status = fhir_to_job_status().get(job_status.upper())
        if not self.job_status:
            raise ValueError(f"Invalid status value, got `{job_status}`")
        self.job_id = kwargs.get('jobId')
        self.message = kwargs.get('message', 'No message')
        self.stack = kwargs.get("stack", 'No stack')


def cancel_job(job_id: str) -> JobStatus:
    """
    Sends a request to FHIR API to abort a job
    Its status will be then set to KILLED if it was not FINISHED already
    """
    if not job_id:
        raise MissingDataError("No job_id provided")
    log_delete_task(job_id, f"Step 1: Job {job_id} cancelled")
    resp, result = SjsClient().delete(job_id)
    log_delete_task(job_id, f"Step 2: treat the response: {resp}, {result}")
    if resp.status_code == status.HTTP_403_FORBIDDEN:
        return JobStatus.finished

    if resp.status_code != status.HTTP_200_OK:
        # temp fix before actual fix in FHIR back-end
        # Message will come from QueryServer. If job is not found,
        # it is either killed or finished.
        # But given our dated_measure had no data as if it was finished,
        # we consider it killed
        raise HTTPError(f"Unexpected response code: {resp.status_code}: "
                        f"{result.get('error', 'no error')} - {result.get('message', 'no message')}")

    if 'status' not in result:
        raise MissingDataError(f"FHIR ERROR: could not read status from response; {result}")

    s = fhir_to_job_status().get(result.get('status').upper())
    try:
        new_status = JobStatus(s)
    except ValueError as ve:
        raise ValueError(f"QUERY SERVER ERROR: status from response ({s}) is not expected. "
                         f"Values can be {[s.value for s in JobStatus]}") from ve

    if new_status not in [JobStatus.cancelled, JobStatus.finished]:
        raise MissingDataError(f"Status returned by FHIR is neither KILLED nor FINISHED -> {result.get('status')}")
    return new_status


def create_job(url: str, json_query: dict, auth_headers: dict) -> Tuple[Response, dict]:
    resp = requests.post(url=url,
                         json=json_query,
                         headers=auth_headers)
    resp.raise_for_status()
    result = resp.json()
    return resp, result


T = TypeVar('T')
LoggerType = Type[Callable[..., None]]


def post_to_sjs(json_query: str, uuid: str, cohort_cls: AbstractCohortRequest, logger: LoggerType) -> T:
    try:
        logger(uuid, f"Step 1: Parse the json query to make it CRB compatible {json_query}")
        cohort_query = CohortQuery(cohortUuid=uuid, **json.loads(json_query))
        logger(uuid, f"Step 2: Send request to sjs: {cohort_query}")
        resp, data = cohort_cls.action(cohort_query)
    except (TypeError, ValueError, ValidationError, HTTPError) as e:
        _logger_err.error(f"Error sending `count` request: {e}")
        return JobServerResponse(success=False, err_msg=str(e), status=JobStatus.failed)
    job_response = JobServerResponse(success=True, **data)
    logger(uuid, f"Step 3: Get the job server response {job_response.__dict__}")
    obj_model = cohort_cls.model
    instance = obj_model.objects.get(pk=uuid)
    if job_response.success:
        instance.request_job_id = job_response.job_id
        if obj_model is CohortResult:
            count = instance.dated_measure.measure
            instance.request_job_status = count >= COHORT_LIMIT and JobStatus.long_pending or JobStatus.pending
    else:
        instance.request_job_status = job_response.job_status
        instance.request_job_fail_msg = job_response.err_msg
    instance.save()
    logger(uuid, f"Done: {job_response.success and obj_model.__name__ + ' updated' or job_response.err_msg}")


def post_count_cohort(auth_headers: dict, json_query: str, dm_uuid: str, global_estimate: bool = False) -> None:
    count_cls, logger = global_estimate and (CohortCountAll, log_count_all_task) or (CohortCount, log_count_task)
    count_request = count_cls(auth_headers=auth_headers, sjs_client=SjsClient())
    post_to_sjs(json_query, dm_uuid, count_request, logger)


def post_create_cohort(auth_headers: dict, json_query: str, cr_uuid: str) -> None:
    cohort_request = CohortCreate(auth_headers=auth_headers, sjs_client=SjsClient())
    post_to_sjs(json_query, cr_uuid, cohort_request, log_create_task)


def post_count_for_feasibility(auth_headers: dict, json_query: str, fs_uuid: str) -> JobServerResponse:
    count_request = CohortCountFeasibility(auth_headers=auth_headers, sjs_client=SjsClient())
    return post_to_sjs(json_query, fs_uuid, count_request, log_feasibility_study_task)
