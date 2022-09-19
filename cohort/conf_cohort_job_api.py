import json

import time
from typing import List, Tuple, Dict

import simplejson
from django.db.models import Model
from django.utils.datetime_safe import datetime
from requests import Response
from rest_framework import status
from rest_framework.request import Request
import environ

from cohort.FhirAPi import FhirCountResponse, FhirCohortResponse, \
    FhirValidateResponse

from admin_cohort.types import JobStatus

env = environ.Env()
COHORT_REQUEST_BUILDER_URL = f"{env('COHORT_REQUEST_BUILDER_URL')}"
JOBS_API = f"{COHORT_REQUEST_BUILDER_URL}/jobs"
CREATE_COHORT_API = f"{COHORT_REQUEST_BUILDER_URL}/create"
GET_COUNT_API = f"{COHORT_REQUEST_BUILDER_URL}/count"
GET_GLOBAL_COUNT_API = f"{COHORT_REQUEST_BUILDER_URL}/countAll"
VALIDATE_QUERY_API = f"{COHORT_REQUEST_BUILDER_URL}/validate"
FHIR_CANCEL_ACTION = "cancel"


def parse_date(str):
    # Parse the date of a post

    # First try all registered possible formats
    possible_formats = [
        '%Y-%m-%d %H:%M:%S.%f',
        '%Y-%m-%dT%H:%M:%S.%fZ',
        '%a, %d %b %Y %H:%M:%S',
        '%a, %d %b %Y %H:%M:%S %z (%Z)',
        '%a, %d %b %Y %H:%M:%S %Z',
        '%a, %d %b %Y %H:%M:%S %z',
        '%d %b %Y %H:%M:%S %z',
        '%a, %d %b %Y %H:%M %z',
        '%a, %d %b %y %H:%M:%S %Z',
        '%d %b %Y %H:%M:%S %Z'
    ]
    for f in possible_formats:
        try:
            return datetime.strptime(str, f)
        except ValueError:
            pass
    raise ValueError("Unsupported date format {}".format(str))


def fhir_to_job_status() -> Dict[str, JobStatus]:
    return dict(
        KILLED=JobStatus.KILLED,
        FINISHED=JobStatus.FINISHED,
        RUNNING=JobStatus.STARTED,
        STARTED=JobStatus.STARTED,
        ERROR=JobStatus.ERROR,
        UNKNOWN=JobStatus.UNKNOWN,
        PENDING=JobStatus.PENDING,
    )


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
        str_ids = [str(id) for id in ids]
        for str_id in str_ids:
            assert str_id.isnumeric()
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
    return dict(
        Authorization=f"Bearer {request.jwt_session_key}"
        if request.jwt_session_key else request.META.get("HTTP_AUTHORIZATION")
    )


class JobResult:
    def __init__(self, resp: Response, **kwargs):
        self._type: str = kwargs.get('_type', None)
        self.source: str = kwargs.get('source', None)

        # count
        if "group.count" in kwargs:
            self.count = kwargs.get("group.count", None)
        else:
            self.count = kwargs.get("count", None)
        self.count_male = kwargs.get("count_male", None)
        self.count_unknown = kwargs.get("count_unknown", None)
        self.count_deceased = kwargs.get("count_deceased", None)
        self.count_alive = kwargs.get("count_alive", None)
        self.count_female = kwargs.get("count_female", None)
        self.count_min = kwargs.get("minimum", None)
        self.count_max = kwargs.get("maximum", None)

        # cohort
        self.group_id = kwargs.get("group.id", None)

        # case of error
        self.message = kwargs.get(
            'message', f'could not read the message. Full response: {resp.text}'
        )
        self.stack = kwargs.get("stack", resp.text)


def init_result_from_response_dict(resp: Response, result: dict) -> JobResult:
    return JobResult(resp, **result)


class JobResponse:
    def __init__(self, resp: Response, **kwargs):
        self.duration: str = kwargs.get('duration', None)
        self.class_path: str = kwargs.get('classPath', None)
        start_time: str = kwargs.get('startTime', None)
        self.start_time: datetime = parse_date(start_time) \
            if start_time else None
        self.context: str = kwargs.get('context', None)
        self.status: JobStatus = fhir_to_job_status().get(
            kwargs.get('status', None), None
        )
        if self.status is None:
            print(f"ERROR EXPECTED : status is None : {resp.json()}")
        self.job_id: str = kwargs.get('jobId', None)
        self.context_id: str = kwargs.get('contextId', None)

        job_result = kwargs.get('result', [])

        self.result: List[JobResult] = [
            init_result_from_response_dict(resp, d)
            for d in job_result
        ] if isinstance(job_result, list) else [
            init_result_from_response_dict(resp, job_result)
        ]
        if len(self.result) < 1 \
                and self.status in [JobStatus.FINISHED.name, JobStatus.ERROR.name]:
            raise Exception(f"FHIR ERROR: Result is empty - {resp.text}")

        self.request_response: Response = resp


def init_job_from_response(resp: Response, result: dict) -> JobResponse:
    return JobResponse(resp, **result)


def get_job(job_id: str, auth_headers) -> Tuple[Response, dict]:
    import requests
    try:
        resp = requests.get(
            f"{JOBS_API}/{job_id}", headers=auth_headers
        )
    except Exception as e:
        raise Exception(f"INTERNAL ERROR: {e}")

    try:
        result = resp.json()
    except Exception as e:
        raise Exception(f"QUERY SERVER ERROR {resp.status_code}: {resp}")

    if resp.status_code != 200:
        raise Exception(
            f"INTERNAL CONNECTION ERROR {resp.status_code}: "
            f"{result.get('error', 'no error')} ; "
            f"{result.get('message', 'no message')}"
        )

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
        resp = requests.patch(
            f"{JOBS_API}/{job_id}/{FHIR_CANCEL_ACTION}", headers=auth_headers
        )
    except Exception as e:
        raise Exception(f"INTERNAL ERROR: {e}")

    try:
        result = resp.json()
    except Exception:
        raise Exception(f"QUERY SERVER ERROR {resp.status_code}: {resp}")

    if resp.status_code == status.HTTP_403_FORBIDDEN:
        return JobStatus.FINISHED

    if resp.status_code != status.HTTP_200_OK:
        # temp fix before actual fix in FHIR back-end
        # Message will come from QueryServer. If job is not found,
        # it is either killed or finished.
        # But given our dated_measure had no data as if it was finished,
        # we consider it killed
        raise Exception(
            f"INTERNAL CONNECTION ERROR {resp.status_code}: "
            f"{result.get('error', 'no error')} ; "
            f"{result.get('message', 'no message')}"
        )

    if 'status' not in result:
        raise Exception(
            f"FHIR ERROR: could not read status from response ; {str(result)}"
        )

    s = result.get('status', "").lower()
    try:
        new_status = JobStatus(s)
    except ValueError:
        raise Exception(
            f"QUERY SERVER ERROR: status from response ({s}) is not expected. "
            f"Values can be {[v.value for v in JobStatus]}")

    if new_status not in [JobStatus.KILLED, JobStatus.FINISHED]:
        raise Exception(
            f"DATA ERROR: status returned by FHIR is neither KILLED or "
            f"FINISHED -> {str(result)}"
        )
    print(f"QueryServer Job {job_id} cancelled.")
    return new_status


def create_count_job(
        json_file: str, auth_headers, global_estimate
) -> Tuple[Response, dict]:
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
        resp = requests.post(
            GET_GLOBAL_COUNT_API if global_estimate else GET_COUNT_API,
            json=json.loads(json_file), headers=auth_headers
        )
    except Exception as e:
        raise Exception(f"INTERNAL ERROR: {e}")

    try:
        result = resp.json()
    except (simplejson.JSONDecodeError, json.JSONDecodeError, ValueError):
        raise Exception(f"QUERY SERVER ERROR {resp.status_code}: {resp}")

    if resp.status_code != 200:
        raise Exception(
            f"INTERNAL CONNECTION ERROR {resp.status_code}: "
            f"{result.get('error', 'no error')} ; "
            f"{result.get('message', 'no message')}"
        )

    return resp, result


def post_count_cohort(
        json_file: str, auth_headers, log_prefix: str = "",
        dated_measure: Model = None, global_estimate: bool = False
) -> FhirCountResponse:
    """
    Called to ask a Fhir API to compute the size of a cohort given
    the request in the json_file
    :param json_file:
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
        return FhirCountResponse(
            job_duration=datetime.now() - d, success=False,
            err_msg="No dated_measure was provided "
                    "to be updated during the process",
            fhir_job_status=JobStatus.ERROR
        )

    try:
        resp, result = create_count_job(
            json_file, auth_headers, global_estimate
        )
    except Exception as e:
        return FhirCountResponse(
            job_duration=datetime.now() - d, success=False, err_msg=str(e),
            fhir_job_status=JobStatus.ERROR
        )

    print(f"{log_prefix} Step 2: Response being processed")
    try:
        job = init_job_from_response(resp, result)
    except Exception as e:
        return FhirCountResponse(
            job_duration=datetime.now() - d, success=False,
            err_msg=f"Error while interpreting response: {e} - {resp.text}",
            fhir_job_status=JobStatus.ERROR
        )

    if job.status == JobStatus.ERROR:
        job_result = job.result[0]
        reason = job_result.message
        if len(reason) == 0:
            if job_result.stack is None or len(job_result.stack) == 0:
                reason = f'message and stack message are empty. ' \
                         f'Full result: {resp.text}'
            else:
                reason = f'message is empty. Stack message: {job_result.stack}'

        err_msg = f"FHIR ERROR {job.request_response.status_code}: {reason}"
        return FhirCountResponse(
            job_duration=datetime.now() - d, success=False, err_msg=err_msg,
            fhir_job_status=JobStatus.ERROR
        )

    dated_measure.request_job_status = job.status.name.lower()
    dated_measure.request_job_id = job.job_id
    dated_measure.save()

    err_cnt = 0
    print(f"{log_prefix} Step 3: Job created. Waiting for it to be finished")
    while job.status not in [
        JobStatus.KILLED, JobStatus.FINISHED, JobStatus.ERROR
    ]:
        time.sleep(2)
        try:
            res, result = get_job(job.job_id, auth_headers=auth_headers)
            job = init_job_from_response(resp=res, result=result)
            print(
                f"{log_prefix} Step 3.x: Job created. Status: {job.status}."
            )
        except Exception as e:
            err_cnt += 1
            print(
                f"{log_prefix} Step 3.x: "
                f"Error {err_cnt} found on getting status : {str(e)}. "
                f"Waiting 10s."
            )
            if err_cnt > 5:
                return FhirCountResponse(
                    job_duration=datetime.now() - d, success=False,
                    err_msg=f"5 errors in a row while getting "
                            f"job status : {str(e)}",
                    fhir_job_status=JobStatus.ERROR
                )
            time.sleep(10)

    print(f"{log_prefix} Step 4: Job ended, returning result.")
    if job.status == JobStatus.KILLED:
        return FhirCountResponse(
            job_duration=datetime.now() - d, success=False,
            err_msg=f"Job was cancelled", fhir_job_status=JobStatus.KILLED
        )

    if job.status == JobStatus.ERROR:
        return FhirCountResponse(
            job_duration=datetime.now() - d, success=False,
            err_msg=job.result[0].message, fhir_job_status=JobStatus.ERROR
        )

    job_result = job.result[0]
    if job_result.count is None and job_result.count_max is None:
        err_msg = f"INTERNAL ERROR: format of received " \
                  f"response not anticipated: {str(result)}"
        return FhirCountResponse(
            fhir_job_id=job.job_id, job_duration=datetime.now() - d,
            success=False, err_msg=err_msg,
            fhir_job_status=JobStatus.ERROR
        )

    return FhirCountResponse(
        fhir_datetime=datetime.now(),
        fhir_job_id=job.job_id,
        job_duration=datetime.now() - d,
        success=True,
        count=job_result.count,
        count_male=job_result.count_male,
        count_unknown=job_result.count_unknown,
        count_deceased=job_result.count_deceased,
        count_alive=job_result.count_alive,
        count_female=job_result.count_female,
        count_min=job_result.count_min,
        count_max=job_result.count_max,
        fhir_job_status=job.status,
    )


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
        resp = requests.post(
            CREATE_COHORT_API, json=json.loads(json_file), headers=auth_headers
        )
    except Exception as e:
        raise Exception(f"INTERNAL ERROR: {e}")

    try:
        result = resp.json()
    except Exception:
        raise Exception(
            f"INTERNAL ERROR {resp.status_code}: could not read result from "
            f"request to FHIR ({resp.text if resp.text else str(resp)})"
        )

    if resp.status_code != 200:
        raise Exception(
            f"INTERNAL CONNECTION ERROR {resp.status_code}: "
            f"{result.get('error', 'no error')} ; "
            f"{result.get('message', 'no message')}"
        )

    return resp, result


def post_create_cohort(
        json_file: str, auth_headers, log_prefix: str = "",
        cohort_result: Model = None
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
        return FhirCohortResponse(
            job_duration=datetime.now() - d, success=False,
            err_msg="No dated_measure was provided "
                    "to be updated during the process",
            fhir_job_status=JobStatus.ERROR
        )

    try:
        resp, result = create_cohort_job(json_file, auth_headers)
    except Exception as e:
        return FhirCohortResponse(
            job_duration=datetime.now() - d, success=False, err_msg=str(e),
            fhir_job_status=JobStatus.ERROR
        )

    print(f"{log_prefix} Step 2: Response being processed")
    try:
        job = init_job_from_response(resp=resp, result=result)
    except Exception as e:
        return FhirCohortResponse(
            job_duration=datetime.now() - d, success=False, err_msg=str(e),
            fhir_job_status=JobStatus.ERROR
        )

    if job.status == JobStatus.ERROR:
        job_result = job.result[0]
        reason = job_result.message
        if len(reason) == 0:
            if job_result.stack is None or len(job_result.stack) == 0:
                reason = f'message and stack message are empty. ' \
                         f'Full result: {resp.text}'
            else:
                reason = f'message is empty. Stack message: {job_result.stack}'

        err_msg = f"FHIR ERROR {job.request_response.status_code}: {reason}"
        return FhirCohortResponse(
            job_duration=datetime.now() - d, success=False, err_msg=err_msg,
            fhir_job_status=JobStatus.ERROR
        )

    print(f"{log_prefix} Step 3: Job created. Waiting for it to be finished")

    cohort_result.request_job_status = job.status.name.lower()
    cohort_result.request_job_id = job.job_id
    cohort_result.save()
    cohort_result.dated_measure.request_job_status = \
        job.status.name.lower()
    cohort_result.dated_measure.request_job_id = job.job_id
    cohort_result.dated_measure.save()

    err_cnt = 0
    while job.status not in [
        JobStatus.KILLED, JobStatus.FINISHED, JobStatus.ERROR
    ]:
        time.sleep(5)
        try:
            res, result = get_job(job.job_id, auth_headers=auth_headers)
            job = init_job_from_response(res, result)
        except Exception as e:
            err_cnt += 1
            print(
                f"{log_prefix} Step 3.x: "
                f"Error {err_cnt} found on getting status : {str(e)}"
            )
            if err_cnt > 5:
                return FhirCohortResponse(
                    job_duration=datetime.now() - d, success=False,
                    err_msg=f"5 errors in a row while getting "
                            f"job status : {str(e)}",
                    fhir_job_status=JobStatus.ERROR,
                )
            time.sleep(15)

    print(f"{log_prefix} Step 4: Job stopped, returning result.")
    if job.status == JobStatus.KILLED:
        return FhirCohortResponse(
            job_duration=datetime.now() - d, success=False,
            err_msg=f"Job was cancelled",
            fhir_job_status=JobStatus.KILLED,
        )

    if job.status == JobStatus.ERROR:
        return FhirCohortResponse(
            job_duration=datetime.now() - d, success=False,
            err_msg=job.result[0].message, fhir_job_status=JobStatus.ERROR
        )

    job_result = job.result[0]
    if not job_result.group_id or job_result.count is None:
        err_msg = f"INTERNAL ERROR: missing result count or group.id: " \
                  f"{str(result)}"
        return FhirCohortResponse(
            fhir_job_id=job.job_id, job_duration=datetime.now() - d,
            success=False, err_msg=err_msg, fhir_job_status=JobStatus.ERROR,

        )

    return FhirCohortResponse(
        fhir_job_id=job.job_id,
        fhir_datetime=datetime.now(),
        job_duration=datetime.now() - d,
        success=True,
        count=job_result.count,
        group_id=job_result.group_id,
        fhir_job_status=job.status,
    )


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
