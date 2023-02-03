import json
import os
import time
from typing import List, Tuple, Dict

import requests
from requests import Response
import simplejson
from django.utils import timezone
from django.utils.datetime_safe import datetime
from rest_framework import status
from rest_framework.request import Request

from admin_cohort.types import JobStatus
from cohort.crb_responses import CRBCountResponse, CRBCohortResponse, CRBValidateResponse
from cohort.tools import log_count_task, log_create_task

COHORT_REQUEST_BUILDER_URL = os.environ.get('COHORT_REQUEST_BUILDER_URL')
JOBS_API = f"{COHORT_REQUEST_BUILDER_URL}/jobs"
CREATE_COHORT_API = f"{COHORT_REQUEST_BUILDER_URL}/create"
COUNT_API = f"{COHORT_REQUEST_BUILDER_URL}/count"
GLOBAL_COUNT_API = f"{COHORT_REQUEST_BUILDER_URL}/countAll"
VALIDATE_QUERY_API = f"{COHORT_REQUEST_BUILDER_URL}/validate"
FHIR_CANCEL_ACTION = "cancel"


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
    key = request.jwt_session_key or request.META.get("HTTP_AUTHORIZATION")
    return {"Authorization": f"Bearer {key}"}


class JobResult:
    def __init__(self, resp: Response, **kwargs):
        self.source: str = kwargs.get('source')
        self.count = kwargs.get("group.count", kwargs.get("count"))
        self.count_min = kwargs.get("minimum")
        self.count_max = kwargs.get("maximum")
        self.group_id = kwargs.get("group.id")
        self.message = kwargs.get('message', f'could not read the message. Full response: {resp.text}')
        self.stack = kwargs.get("stack", resp.text)


def init_result_from_response_dict(resp: Response, result: dict) -> JobResult:
    return JobResult(resp, **result)


class JobResponse:
    def __init__(self, resp: Response, **kwargs):
        self.duration: str = kwargs.get('duration')
        self.class_path: str = kwargs.get('classPath')
        self.start_time: datetime = kwargs.get('startTime') and parse_date(kwargs.get('startTime')) or None
        self.context: str = kwargs.get('context')
        self.status: JobStatus = fhir_to_job_status().get(kwargs.get('status'))
        if not self.status:
            raise ValueError(f"Expected valid status value, got None : {resp.json()}")
        self.job_id: str = kwargs.get('jobId')
        self.context_id: str = kwargs.get('contextId')

        job_result = kwargs.get('result', [])
        if isinstance(job_result, list):
            self.result: List[JobResult] = [init_result_from_response_dict(resp, jr) for jr in job_result]
        else:
            self.result: List[JobResult] = [init_result_from_response_dict(resp, job_result)]
        if not self.result and self.status in [JobStatus.finished, JobStatus.failed]:
            raise Exception(f"FHIR ERROR: Result is empty - {resp.text}")
        self.request_response: Response = resp


def get_job(job_id: str, auth_headers) -> Tuple[Response, dict]:
    try:
        resp = requests.get(f"{JOBS_API}/{job_id}", headers=auth_headers)
    except Exception as e:
        raise Exception(f"INTERNAL ERROR: {e}")
    try:
        result = resp.json()
    except Exception:
        raise Exception(f"QUERY SERVER ERROR {resp.status_code}: {resp}")

    if resp.status_code != 200:
        raise Exception(f"INTERNAL CONNECTION ERROR {resp.status_code}: "
                        f"{result.get('error', 'no error')} ; "
                        f"{result.get('message', 'no message')}")
    return JobResponse(resp, **result)


def cancel_job(job_id: str, auth_headers) -> JobStatus:
    """
    Sends a request to FHIR API to abort a job
    Its status will be then set to KILLED if it was not FINISHED already
    """
    if not job_id:
        raise Exception("INTERNAL ERROR: no job_id provided")
    try:
        resp = requests.patch(f"{JOBS_API}/{job_id}/{FHIR_CANCEL_ACTION}", headers=auth_headers)
    except Exception as e:
        raise Exception(f"Error while cancelling job on FHIR: {e}")

    try:
        result = resp.json()
    except Exception:
        raise Exception(f"QUERY SERVER ERROR {resp.status_code}: {resp}")

    if resp.status_code == status.HTTP_403_FORBIDDEN:
        return JobStatus.finished

    if resp.status_code != status.HTTP_200_OK:
        # temp fix before actual fix in FHIR back-end
        # Message will come from QueryServer. If job is not found,
        # it is either killed or finished.
        # But given our dated_measure had no data as if it was finished,
        # we consider it killed
        raise Exception(f"INTERNAL CONNECTION ERROR {resp.status_code}: "
                        f"{result.get('error', 'no error')} - {result.get('message', 'no message')}")

    if 'status' not in result:
        raise Exception(f"FHIR ERROR: could not read status from response; {result}")

    s = fhir_to_job_status().get(result.get('status'))
    try:
        new_status = JobStatus(s)
    except ValueError:
        raise Exception(f"QUERY SERVER ERROR: status from response ({s}) is not expected. "
                        f"Values can be {[s.value for s in JobStatus]}")

    if new_status not in [JobStatus.cancelled, JobStatus.finished]:
        raise Exception(f"DATA ERROR: status returned by FHIR is neither KILLED or FINISHED -> {result}")
    return new_status


def create_count_job(auth_headers: dict, json_query: str, global_estimate) -> Tuple[Response, dict]:
    try:
        resp = requests.post(url=GLOBAL_COUNT_API if global_estimate else COUNT_API,
                             json=json.loads(json_query),
                             headers=auth_headers)
    except Exception as e:
        raise Exception(f"INTERNAL ERROR: {e}")

    try:
        result = resp.json()
    except (simplejson.JSONDecodeError, json.JSONDecodeError, ValueError):
        raise Exception(f"QUERY SERVER ERROR {resp.status_code}: {resp}")

    if resp.status_code != 200:
        raise Exception(f"INTERNAL CONNECTION ERROR {resp.status_code}: "
                        f"{result.get('error', 'no error')}, {result.get('message', 'no message')}")
    return resp, result


def post_count_cohort(auth_headers: dict, json_query: str, dm_uuid: str, global_estimate=False) -> CRBCountResponse:
    from datetime import datetime
    d = datetime.now()
    log_count_task(dm_uuid, "Step 1: Posting count request", global_estimate=global_estimate)

    try:
        resp, result = create_count_job(auth_headers, json_query, global_estimate)
    except Exception as e:
        return CRBCountResponse(success=False,
                                job_duration=datetime.now() - d,
                                fhir_job_status=JobStatus.failed,
                                err_msg=str(e))

    log_count_task(dm_uuid, "Step 2: Response being processed", global_estimate=global_estimate)
    try:
        job = JobResponse(resp, **result)
    except Exception as e:
        return CRBCountResponse(success=False,
                                job_duration=datetime.now() - d,
                                fhir_job_status=JobStatus.failed,
                                err_msg=f"Error while interpreting response: {e} - {resp.text}")

    if job.status == JobStatus.failed:
        job_result = job.result[0]
        reason = job_result.message
        if reason:
            if job_result.stack is None or len(job_result.stack) == 0:
                reason = f'message and stack message are empty. Full result: {resp.text}'
            else:
                reason = f'message is empty. Stack message: {job_result.stack}'
        err_msg = f"FHIR ERROR {job.request_response.status_code}: {reason}"
        return CRBCountResponse(success=False,
                                job_duration=datetime.now() - d,
                                fhir_job_status=JobStatus.failed,
                                err_msg=err_msg)

    log_count_task(dm_uuid, "Step 3: Job created. Waiting for it to be finished", global_estimate=global_estimate)
    errors_count = 0
    while job.status not in [JobStatus.cancelled, JobStatus.finished, JobStatus.failed]:
        time.sleep(2)
        try:
            job = get_job(job.job_id, auth_headers=auth_headers)
            log_count_task(dm_uuid, "Step 3.x: Job created. Status: {job.status}.", global_estimate=global_estimate)
        except Exception as e:
            errors_count += 1
            log_count_task(dm_uuid, f"Step 3.x: Error {errors_count} found on getting status : {e}.",
                           global_estimate=global_estimate)
            if errors_count > 5:
                return CRBCountResponse(success=False,
                                        job_duration=datetime.now() - d,
                                        fhir_job_status=JobStatus.failed,
                                        err_msg=f"5 errors in a row while getting job status : {e}")
            time.sleep(10)

    log_count_task(dm_uuid, "Step 4: Job ended, returning result.", global_estimate=global_estimate)
    if job.status in (JobStatus.cancelled, JobStatus.failed):
        return CRBCountResponse(success=False,
                                job_duration=datetime.now() - d,
                                fhir_job_status=job.status,
                                err_msg=job.status == JobStatus.failed and job.result[0].message or "Job cancelled")

    job_result = job.result[0]
    if job_result.count is None and job_result.count_max is None:
        err_msg = f"INTERNAL ERROR: format of received response not anticipated: {job_result}"
        return CRBCountResponse(success=False,
                                fhir_job_id=job.job_id,
                                job_duration=datetime.now() - d,
                                fhir_job_status=JobStatus.failed,
                                err_msg=err_msg)

    return CRBCountResponse(fhir_datetime=timezone.now(),
                            fhir_job_id=job.job_id,
                            job_duration=datetime.now() - d,
                            success=True,
                            count=job_result.count,
                            count_min=job_result.count_min,
                            count_max=job_result.count_max,
                            fhir_job_status=job.status)


def create_cohort_job(auth_headers: dict, json_query: dict) -> Tuple[Response, dict]:
    try:
        resp = requests.post(url=CREATE_COHORT_API, json=json_query, headers=auth_headers)
    except Exception as e:
        raise Exception(f"INTERNAL ERROR: {e}")
    result = {}
    try:
        result = resp.json()
    except Exception:
        raise Exception(f"INTERNAL ERROR {resp.status_code}: could not read result from "
                        f"request to CRB ({resp.text or str(resp)})")
    if resp.status_code != 200:
        raise Exception(f"INTERNAL CONNECTION ERROR {resp.status_code}: "
                        f"{result.get('error', 'no error')}, {result.get('message', 'no message')}")
    return resp, result


def post_create_cohort(auth_headers: dict, json_query: str, cr_uuid: str) -> CRBCohortResponse:
    log_create_task(cr_uuid, "Step 1: Post cohort creation request to CRB")
    try:
        json_query = json.loads(json_query)
        json_query["cohortUuid"] = cr_uuid
        resp, result = create_cohort_job(auth_headers, json_query)
    except (json.JSONDecodeError, TypeError, Exception) as e:
        return CRBCohortResponse(success=False, fhir_job_status=JobStatus.failed, err_msg=str(e))

    log_create_task(cr_uuid, "Step 2: Processing CRB response")
    try:
        job = JobResponse(resp, **result)
    except Exception as e:
        return CRBCohortResponse(success=False, fhir_job_status=JobStatus.failed, err_msg=str(e))

    log_create_task(cr_uuid, "Step 3: SJS job created. Will be notified later by callback")
    return CRBCohortResponse(success=True, fhir_job_id=job.job_id)


def post_validate_cohort(json_query: str, auth_headers) -> CRBValidateResponse:
    """ Called to ask a Fhir API to validate the format of the json_query """
    return CRBValidateResponse(success=True)

    # todo
    # try:
    #     resp = requests.post(VALIDATE_QUERY_API, json=json.loads(json_query), headers=auth_headers)
    # except Exception as e:
    #     err_msg = f"INTERNAL ERROR: {e}"
    #     return CRBValidateResponse(success=False, err_msg=err_msg)
    # else:
    #     result = resp.json()
    #
    #     if resp.status_code != 200:
    #         err_msg = f"INTERNAL CONNECTION ERROR {resp.status_code}: {result['message']}"
    #         return CRBValidateResponse(success=False, err_msg=err_msg)
    #
    #     else:
    #         try:
    #             validated = result["result"][0]["validated"]
    #         except Exception as e:
    #             err_msg = f"INTERNAL ERROR: format of received response not anticipated: {e}"
    #             return CRBValidateResponse(success=False, err_msg=err_msg)
    #         else:
    #             return CRBValidateResponse(success=validated)
