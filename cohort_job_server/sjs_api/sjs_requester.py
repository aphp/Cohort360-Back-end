import json
from typing import Type, Callable

from pydantic import ValidationError
from requests import HTTPError
from rest_framework import status

from admin_cohort.settings import COHORT_LIMIT
from admin_cohort.types import JobStatus, MissingDataError
from cohort.models import CohortResult
from cohort_job_server.sjs_api import BaseCohortRequest, CohortQuery, SJSClient, SJSResponse, sjs_status_mapper
from cohort_job_server.utils import _logger_err


LoggerType = Type[Callable[..., None]]


class SJSRequester:
    @staticmethod
    def post_to_job_server(json_query: str, instance_id: str, cohort_request: BaseCohortRequest, logger: LoggerType) -> SJSResponse:
        try:
            logger(instance_id, f"Step 1: Converting the json query: {json_query}")
            cohort_query = CohortQuery(cohortUuid=instance_id, **json.loads(json_query))
            logger(instance_id, f"Step 2: Sending request to Job Server: {cohort_query}")
            response = cohort_request.launch(cohort_query)
        except (TypeError, ValueError, ValidationError, HTTPError) as e:
            _logger_err.error(f"Error sending request to Job Server: {e}")
            job_server_resp = SJSResponse(success=False, err_msg=str(e), status="ERROR")
        else:
            job_server_resp = SJSResponse(success=True, **response.json())
        logger(instance_id, f"Step 3: Received Job Server response {job_server_resp.__dict__}")
        obj_model = cohort_request.model
        instance = obj_model.objects.get(pk=instance_id)
        if job_server_resp.success:
            instance.request_job_id = job_server_resp.job_id
            if obj_model is CohortResult:
                count = instance.dated_measure.measure
                instance.request_job_status = count >= COHORT_LIMIT and JobStatus.long_pending or JobStatus.pending
        else:
            instance.request_job_status = job_server_resp.job_status
            instance.request_job_fail_msg = job_server_resp.err_msg
        instance.save()
        logger(instance_id, f"Done: {job_server_resp.success and f'{obj_model.__name__} updated' or job_server_resp.err_msg}")
        return job_server_resp

    @staticmethod
    def cancel_job(job_id: str) -> JobStatus:
        assert job_id is not None, "Missing `job_id`"
        response = SJSClient().delete(job_id)
        result = response.json()
        if response.status_code == status.HTTP_403_FORBIDDEN:
            return JobStatus.finished
        if response.status_code != status.HTTP_200_OK:
            raise HTTPError(f"Request failed: {response.status_code}: "
                            f"{result.get('error', 'no error')} - {result.get('message', 'no message')}")
        if 'status' not in result:
            raise MissingDataError(f"Missing `status` from response: {result}")
        job_status = sjs_status_mapper(result.get('status'))
        if job_status not in [JobStatus.cancelled, JobStatus.finished]:
            raise ValueError(f"Invalid job status {result.get('status')}")
        return job_status
