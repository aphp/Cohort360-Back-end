import json
import logging
import os
import time
from typing import List, Tuple, Dict

import simplejson
from django.db.models import Model
from django.utils import timezone
from django.utils.datetime_safe import datetime
from requests import Response
from rest_framework import status
from rest_framework.request import Request

from admin_cohort.types import JobStatus
from cohort.FhirAPi import FhirCountResponse, FhirCohortResponse, FhirValidateResponse

_log = logging.getLogger('info')

COHORT_REQUEST_BUILDER_URL = os.environ.get('COHORT_REQUEST_BUILDER_URL')
JOBS_API = f"{COHORT_REQUEST_BUILDER_URL}/jobs"
CREATE_COHORT_API = f"{COHORT_REQUEST_BUILDER_URL}/create"
GET_COUNT_API = f"{COHORT_REQUEST_BUILDER_URL}/count"
GET_GLOBAL_COUNT_API = f"{COHORT_REQUEST_BUILDER_URL}/countAll"
VALIDATE_QUERY_API = f"{COHORT_REQUEST_BUILDER_URL}/validate"
FHIR_CANCEL_ACTION = "cancel"


def parse_date(d):
    # Parse the date of a post

    # First try all registered possible formats
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
            "PENDING": JobStatus.pending}


def format_json_request(json_req: str) -> str:
    """
    Called to format a json query stored in RequestQuerySnapshot
    to the format read by Fhir API
    :param json_req:
    :type json_req:
    :return:
    :rtype:
    """
    return json_req


def retrieve_perimeters(json_req: str) -> [str]:
    """
    Called to retrieve care_site_ids (perimeters) from a Json request
    :param json_req:
    :type json_req:
    :return:
    :rtype:
    """
    # sourcePopulation:{caresiteCohortList: [...ids]}
    try:
        req = json.loads(json_req)
        ids = req["sourcePopulation"]["caresiteCohortList"]
        assert isinstance(ids, list)
        str_ids = []
        for i in ids:
            str_ids.append(str(i))
            assert str(i).isnumeric()
        return str_ids
    except Exception:
        return None


def get_fhir_authorization_header(request: Request) -> dict:
    """
    Called when a request is about to be made to external Fhir API
    :param request:
    :type request:
    :return:
    :rtype:
    """
    key = request.jwt_session_key or request.META.get("HTTP_AUTHORIZATION")
    return {"Authorization": f"Bearer {key}"}


class JobResult:
    def __init__(self, resp: Response, **kwargs):
        self._type: str = kwargs.get('_type')
        self.source: str = kwargs.get('source')
        # count
        if "group.count" in kwargs:
            self.count = kwargs.get("group.count")
        else:
            self.count = kwargs.get("count")
        self.count_min = kwargs.get("minimum")
        self.count_max = kwargs.get("maximum")
        # cohort
        self.group_id = kwargs.get("group.id")
        # case of error
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
            _log.info(f"Expected Error: status is None : {resp.json()}")
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


def init_job_from_response(resp: Response, result: dict) -> JobResponse:
    return JobResponse(resp, **result)


def get_job(job_id: str, auth_headers) -> Tuple[Response, dict]:
    import requests
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

    return resp, result


def cancel_job(job_id: str, auth_headers) -> JobStatus:
    """
    Sends a request to FHIR API to abort a job
    Its status will be then set to KILLED if it was not FINISHED already
    :param job_id:
    :type job_id:
    :param auth_headers:
    :type auth_headers:
    :return:
    :rtype:
    """
    import requests
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
                        f"Values can be {[v.value for v in JobStatus]}")

    if new_status not in [JobStatus.cancelled, JobStatus.finished]:
        raise Exception(f"DATA ERROR: status returned by FHIR is neither KILLED or FINISHED -> {result}")
    _log.info(f"QueryServer Job {job_id} cancelled.")
    return new_status


def create_count_job(json_file: str, auth_headers, global_estimate) -> Tuple[Response, dict]:
    """
    :param json_file:
    :type json_file:
    :param auth_headers:
    :type auth_headers:
    :return:
    :rtype:
    """
    import json
    import requests

    try:
        resp = requests.post(GET_GLOBAL_COUNT_API if global_estimate else GET_COUNT_API, json=json.loads(json_file),
                             headers=auth_headers)
    except Exception as e:
        raise Exception(f"INTERNAL ERROR: {e}")

    try:
        result = resp.json()
    except (simplejson.JSONDecodeError, json.JSONDecodeError, ValueError):
        raise Exception(f"QUERY SERVER ERROR {resp.status_code}: {resp}")

    if resp.status_code != 200:
        raise Exception(f"INTERNAL CONNECTION ERROR {resp.status_code}: "
                        f"{result.get('error', 'no error')} ; "
                        f"{result.get('message', 'no message')}")

    return resp, result


def post_count_cohort(json_file: str, auth_headers, log_prefix: str = "", dated_measure: Model = None,
                      global_estimate: bool = False) -> FhirCountResponse:
    """
    Called to ask a FHIR API to compute the size of a given cohort
    the request in the json_file
    :param: json_file:
    :type json_file:
    :param auth_headers:
    :type auth_headers:
    :param log_prefix:
    :type log_prefix: str
    :param dated_measure:
    :type dated_measure: DatedMeasure
    :return:
    :rtype:
    """
    from datetime import datetime

    d = datetime.now()
    print(f"{log_prefix} Step 1: Posting count request")
    if dated_measure is None:
        return FhirCountResponse(job_duration=datetime.now() - d, success=False, fhir_job_status=JobStatus.failed,
                                 err_msg="No dated_measure was provided to be updated during the process")

    try:
        resp, result = create_count_job(json_file, auth_headers, global_estimate)
    except Exception as e:
        return FhirCountResponse(job_duration=datetime.now() - d, success=False, fhir_job_status=JobStatus.failed,
                                 err_msg=str(e))

    print(f"{log_prefix} Step 2: Response being processed")
    try:
        job = init_job_from_response(resp, result)
    except Exception as e:
        return FhirCountResponse(job_duration=datetime.now() - d, success=False, fhir_job_status=JobStatus.failed,
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
        return FhirCountResponse(job_duration=datetime.now() - d, success=False, fhir_job_status=JobStatus.failed,
                                 err_msg=err_msg)

    dated_measure.request_job_status = job.status.value
    dated_measure.request_job_id = job.job_id
    dated_measure.save()

    err_cnt = 0
    print(f"{log_prefix} Step 3: Job created. Waiting for it to be finished")
    while job.status not in [JobStatus.cancelled, JobStatus.finished, JobStatus.failed]:
        time.sleep(2)
        try:
            res, result = get_job(job.job_id, auth_headers=auth_headers)
            job = init_job_from_response(resp=res, result=result)
            print(f"{log_prefix} Step 3.x: Job created. Status: {job.status}.")
        except Exception as e:
            err_cnt += 1
            print(f"{log_prefix} Step 3.x: Error {err_cnt} found on getting status : {e}. Waiting 10s.")
            if err_cnt > 5:
                return FhirCountResponse(job_duration=datetime.now() - d, success=False,
                                         fhir_job_status=JobStatus.failed, err_msg=f"5 errors in a row while getting "
                                                                                   f"job status : {e}")
            time.sleep(10)

    print(f"{log_prefix} Step 4: Job ended, returning result.")
    if job.status == JobStatus.cancelled:
        return FhirCountResponse(job_duration=datetime.now() - d, success=False, fhir_job_status=JobStatus.cancelled,
                                 err_msg="Job was cancelled")

    if job.status == JobStatus.failed:
        return FhirCountResponse(job_duration=datetime.now() - d, success=False, fhir_job_status=JobStatus.failed,
                                 err_msg=job.result[0].message)

    job_result = job.result[0]
    if job_result.count is None and job_result.count_max is None:
        err_msg = f"INTERNAL ERROR: format of received response not anticipated: {result}"
        return FhirCountResponse(fhir_job_id=job.job_id, job_duration=datetime.now() - d, success=False,
                                 fhir_job_status=JobStatus.failed, err_msg=err_msg)

    return FhirCountResponse(fhir_datetime=timezone.now(),
                             fhir_job_id=job.job_id,
                             job_duration=datetime.now() - d,
                             success=True,
                             count=job_result.count,
                             count_min=job_result.count_min,
                             count_max=job_result.count_max,
                             fhir_job_status=job.status)


def create_cohort_job(json_file: str, auth_headers) -> Tuple[Response, dict]:
    """
    :param json_file:
    :type json_file:
    :param auth_headers:
    :type auth_headers:
    :return:
    :rtype:
    """
    import json
    import requests

    try:
        resp = requests.post(CREATE_COHORT_API, json=json.loads(json_file), headers=auth_headers)
    except Exception as e:
        raise Exception(f"INTERNAL ERROR: {e}")

    try:
        result = resp.json()
    except Exception:
        raise Exception(f"INTERNAL ERROR {resp.status_code}: could not read result from "
                        f"request to FHIR ({resp.text if resp.text else str(resp)})")

    if resp.status_code != 200:
        raise Exception(f"INTERNAL CONNECTION ERROR {resp.status_code}: "
                        f"{result.get('error', 'no error')} ; "
                        f"{result.get('message', 'no message')}")

    return resp, result


def post_create_cohort(json_file: str, auth_headers, log_prefix: str = "", cohort_result: Model = None
                       ) -> FhirCohortResponse:
    """
    Called to ask a Fhir API to create a cohort given the request
    in the json_file
    :param json_file:
    :type json_file:
    :param auth_headers:
    :type auth_headers:
    :param log_prefix:
    :type log_prefix: str
    :param cohort_result:
    :type cohort_result: CohortResult
    :return:
    :rtype:
    """
    from datetime import datetime

    d = datetime.now()
    print(f"{log_prefix} Step 1: Posting cohort request")
    if cohort_result is None:
        return FhirCohortResponse(job_duration=datetime.now() - d, success=False, fhir_job_status=JobStatus.failed,
                                  err_msg="No dated_measure was provided to be updated during the process")

    try:
        resp, result = create_cohort_job(json_file, auth_headers)
    except Exception as e:
        return FhirCohortResponse(job_duration=datetime.now() - d, success=False, fhir_job_status=JobStatus.failed,
                                  err_msg=str(e))

    print(f"{log_prefix} Step 2: Response being processed")
    try:
        job = init_job_from_response(resp=resp, result=result)
    except Exception as e:
        return FhirCohortResponse(job_duration=datetime.now() - d, success=False, fhir_job_status=JobStatus.failed,
                                  err_msg=str(e))

    if job.status == JobStatus.failed:
        job_result = job.result[0]
        reason = job_result.message
        if not reason:
            if not job_result.stack:
                reason = f"message and stack message are empty. Full result: {resp.text}"
            else:
                reason = f"message is empty. Stack message: {job_result.stack}"

        err_msg = f"FHIR ERROR {job.request_response.status_code}: {reason}"
        return FhirCohortResponse(job_duration=datetime.now() - d, success=False, fhir_job_status=JobStatus.failed,
                                  err_msg=err_msg)

    print(f"{log_prefix} Step 3: Job created. Waiting for it to be finished")

    cohort_result.request_job_status = job.status.value
    cohort_result.request_job_id = job.job_id
    cohort_result.save()
    cohort_result.dated_measure.request_job_status = job.status.value
    cohort_result.dated_measure.request_job_id = job.job_id
    cohort_result.dated_measure.save()

    err_cnt = 0
    while job.status not in [JobStatus.cancelled, JobStatus.finished, JobStatus.failed]:
        time.sleep(5)
        try:
            res, result = get_job(job.job_id, auth_headers=auth_headers)
            job = init_job_from_response(res, result)
        except Exception as e:
            err_cnt += 1
            print(f"{log_prefix} Step 3.x: Error {err_cnt} found on getting status : {e}")
            if err_cnt > 5:
                return FhirCohortResponse(job_duration=datetime.now() - d, success=False,
                                          fhir_job_status=JobStatus.failed,
                                          err_msg=f"5 errors in a row while getting job status : {e}")
            time.sleep(15)

    print(f"{log_prefix} Step 4: Job stopped, returning result.")
    if job.status == JobStatus.cancelled:
        return FhirCohortResponse(job_duration=datetime.now() - d, success=False, fhir_job_status=JobStatus.cancelled,
                                  err_msg="Job was cancelled")

    if job.status == JobStatus.failed:
        return FhirCohortResponse(job_duration=datetime.now() - d, success=False, fhir_job_status=JobStatus.failed,
                                  err_msg=job.result[0].message)

    job_result = job.result[0]
    if not job_result.group_id or job_result.count is None:
        err_msg = f"INTERNAL ERROR: missing result count or group.id: {result}"
        return FhirCohortResponse(fhir_job_id=job.job_id, job_duration=datetime.now() - d, success=False,
                                  fhir_job_status=JobStatus.failed, err_msg=err_msg)

    return FhirCohortResponse(fhir_job_id=job.job_id,
                              fhir_datetime=timezone.now(),
                              job_duration=datetime.now() - d,
                              success=True,
                              count=job_result.count,
                              group_id=job_result.group_id,
                              fhir_job_status=job.status)


def post_validate_cohort(json_file: str, auth_headers) -> FhirValidateResponse:
    """
    Called to ask a Fhir API to validate the format of the json_file
    :param json_file:
    :type json_file:
    :param auth_headers:
    :type auth_headers:
    :return:
    :rtype:
    """
    return FhirValidateResponse(success=True)

    # import json
    # import requests
    #
    # try:
    #     resp = requests.post(VALIDATE_QUERY_API, json=json.loads(json_file), headers=auth_headers)
    # except Exception as e:
    #     err_msg = f"INTERNAL ERROR: {e}"
    #     return FhirValidateResponse(success=False, err_msg=err_msg)
    # else:
    #     result = resp.json()
    #
    #     if resp.status_code != 200:
    #         err_msg = f"INTERNAL CONNECTION ERROR {resp.status_code}: {result['message']}"
    #         return FhirValidateResponse(success=False, err_msg=err_msg)
    #
    #     else:
    #         try:
    #             validated = result["result"][0]["validated"]
    #         except Exception as e:
    #             err_msg = f"INTERNAL ERROR: format of received response not anticipated: {e}"
    #             return FhirValidateResponse(success=False, err_msg=err_msg)
    #         else:
    #             return FhirValidateResponse(success=validated)
