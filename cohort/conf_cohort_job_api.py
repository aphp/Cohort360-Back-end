import json
import logging
import os
from typing import Tuple, Dict

import requests
from datetime import datetime
from requests import Response, HTTPError
from rest_framework import status
from rest_framework.request import Request

from admin_cohort.middleware.request_trace_id_middleware import add_trace_id
from admin_cohort.types import JobStatus, MissingDataError
from cohort.crb import CohortQueryBuilder, CRBFactory, FhirRequest
from cohort.crb.format_query import FormatQuery
from cohort.crb_responses import CRBCountResponse, CRBCohortResponse
from cohort.tools import log_count_task, log_create_task

COHORT_REQUEST_BUILDER_URL = os.environ.get('COHORT_REQUEST_BUILDER_URL')
JOBS_API = f"{COHORT_REQUEST_BUILDER_URL}/jobs"
CREATE_COHORT_API = f"{COHORT_REQUEST_BUILDER_URL}/create"
COUNT_API = f"{COHORT_REQUEST_BUILDER_URL}/count"
GLOBAL_COUNT_API = f"{COHORT_REQUEST_BUILDER_URL}/countAll"
VALIDATE_QUERY_API = f"{COHORT_REQUEST_BUILDER_URL}/validate"
FHIR_CANCEL_ACTION = "cancel"

_logger = logging.getLogger("info")
_logger_err = logging.getLogger("django.request")


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
    key = request.jwt_access_key or request.META.get("HTTP_AUTHORIZATION")
    headers = {"Authorization": f"Bearer {key}",
               "authorizationMethod": request.META.get('HTTP_AUTHORIZATIONMETHOD')
               }
    headers = add_trace_id(headers)
    return headers


class JobResponse:
    def __init__(self, resp: Response, **kwargs):
        self.status: JobStatus = fhir_to_job_status().get(kwargs.get('status', '').upper())
        if not self.status:
            raise ValueError(f"Expected valid status value, got None : {resp.json()}")
        self.job_id: str = kwargs.get('jobId')
        self.source: str = kwargs.get('source')
        self.count = kwargs.get("count")
        self.count_min = kwargs.get("minimum")
        self.count_max = kwargs.get("maximum")
        self.group_id = kwargs.get("group.id")
        self.message = kwargs.get('message', f'No message. Full response: {resp.text}')
        self.stack = kwargs.get("stack", resp.text)
        self.request_response: Response = resp


def cancel_job(job_id: str, auth_headers) -> JobStatus:
    """
    Sends a request to FHIR API to abort a job
    Its status will be then set to KILLED if it was not FINISHED already
    """
    if not job_id:
        raise MissingDataError("No job_id provided")
    resp = requests.patch(f"{JOBS_API}/{job_id}/{FHIR_CANCEL_ACTION}", headers=auth_headers)
    resp.raise_for_status()
    result = resp.json()
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


def post_count_cohort(auth_headers: dict, json_query: str, dm_uuid: str, global_estimate=False) -> CRBCountResponse:
    try:
        log_count_task(dm_uuid, "Step 1: Posting count request", global_estimate=global_estimate)
        json_query = json.loads(json_query)
        json_query["cohortUuid"] = dm_uuid  # todo: rename param to `dm_uuid` once CRB is moved to Django
        resp, result = create_job(url=GLOBAL_COUNT_API if global_estimate else COUNT_API,
                                  json_query=json_query,
                                  auth_headers=auth_headers)
        log_count_task(dm_uuid, "Step 2: Processing CRB response", global_estimate=global_estimate)
        job = JobResponse(resp, **result)
    except (TypeError, ValueError, HTTPError) as e:
        _logger_err.error(f"Error sending `count` request: {e}")
        return CRBCountResponse(success=False,
                                fhir_job_status=JobStatus.failed,
                                err_msg=str(e))
    log_create_task(dm_uuid, "Step 3: SJS job created. Will be patched later by callback")
    return CRBCountResponse(success=True, fhir_job_id=job.job_id)


def post_create_cohort(auth_headers: dict, json_query: str, cr_uuid: str) -> CRBCohortResponse:

    log_create_task(cr_uuid, f"Step 1: Generate CRB of {cr_uuid=} with {json_query=} and {auth_headers=}")
    crb = CRBFactory(CohortQueryBuilder(cr_uuid, FormatQuery(auth_headers))).create_cohort_create()
    log_create_task(cr_uuid, "Step 2: Parse the json query to make it CRB compatible")
    fhir_request: FhirRequest = FhirRequest(cohort_uuid=cr_uuid, **json.loads(json_query))

    try:
        log_create_task(cr_uuid, f"Step 3: Send request to sjs: {fhir_request}")
        resp, data = crb.request_to_sjs(fhir_request)
        job = JobResponse(resp, **data)
        log_create_task(cr_uuid, f"Step 4: Get the response {job.__dict__=}")
        return CRBCohortResponse(success=True, fhir_job_id=job.job_id)
    except (TypeError, ValueError, HTTPError) as e:
        _logger_err.error(f"Error sending `cohort creation` request: {e}")
        return CRBCohortResponse(success=False,
                                 fhir_job_status=JobStatus.failed,
                                 err_msg=str(e))


    # try:
    #     log_create_task(cr_uuid, "Step 1: Post cohort creation request to CRB")
    #     json_query = json.loads(json_query)
    #     json_query["cohortUuid"] = cr_uuid
    #     resp, result = create_job(url=CREATE_COHORT_API,
    #                               json_query=json_query,
    #                               auth_headers=auth_headers)
    #     log_create_task(cr_uuid, "Step 2: Processing CRB response")
    #     job = JobResponse(resp, **result)
    #     log_create_task(cr_uuid, f"Step 2.1: {job.__dict__=}")
    # except (TypeError, ValueError, HTTPError) as e:
    #     _logger_err.error(f"Error sending `cohort creation` request: {e}")
    #     return CRBCohortResponse(success=False,
    #                              fhir_job_status=JobStatus.failed,
    #                              err_msg=str(e))
    # log_create_task(cr_uuid, "Step 3: SJS job created. Will be patched later by callback")
    # return CRBCohortResponse(success=True, fhir_job_id=job.job_id)
    #

