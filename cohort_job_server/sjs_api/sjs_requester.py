import json
from typing import Type, Callable

from django.conf import settings
from django.db.models import Model
from requests import HTTPError
from rest_framework import status

from admin_cohort.types import JobStatus, MissingDataError
from cohort.models import CohortResult
from cohort_job_server.sjs_api import BaseCohortRequest, CohortQuery, SJSClient, SJSResponse, sjs_status_mapper
from cohort_job_server.utils import _logger_err


LoggerType = Type[Callable[..., None]]


class SJSRequester:

    def launch_request(self, cohort_request: BaseCohortRequest) -> SJSResponse:
        _logger = cohort_request.log
        instance_id = cohort_request.instance_id
        json_query = cohort_request.json_query
        try:
            _logger(msg=f"Converting the json query: {json_query}")
            cohort_query = CohortQuery(instance_id=instance_id, **json.loads(json_query))
            response = cohort_request.launch(cohort_query)
        except Exception as e:
            _logger_err.error(f"Error sending request to SJS: {e}")
            response_data = dict(success=False, err_msg=str(e), status="ERROR")
        else:
            response_data = dict(success=True, **response.json())
        response = SJSResponse(**response_data)
        _logger(msg=f"Received SJS response {response.__dict__}")
        if instance_id is not None and cohort_request.model is not None:
            self.update_request_instance(cohort_request.model, instance_id, response)
        _logger(msg=f"Done: {response.success and f'{cohort_request.model.__name__} updated' or response.err_msg}")
        return response

    @staticmethod
    def update_request_instance(instance_model: Model, instance_id: str, response: SJSResponse) -> None:
        instance = instance_model.objects.get(pk=instance_id)
        job_status = response.job_status
        if response.success:
            instance.request_job_id = response.job_id
            if instance_model is CohortResult:
                count = instance.dated_measure.measure
                job_status = count >= settings.COHORT_LIMIT and JobStatus.long_pending or JobStatus.pending
        else:
            instance.request_job_fail_msg = response.err_msg
        instance.request_job_status = job_status
        instance.save()

    @staticmethod
    def cancel_job(job_id: str) -> JobStatus:
        try:
            response = SJSClient().delete(job_id)
            result = response.json()
        except json.JSONDecodeError as e:
            raise ValueError(f"Error with response content: {str(e)}")
        if response.status_code == status.HTTP_403_FORBIDDEN:
            return JobStatus.finished
        if response.status_code != status.HTTP_200_OK:
            raise HTTPError(f"Cancel request failed: {response.status_code}: {result}")
        if 'status' not in result:
            raise MissingDataError(f"`status` is missing in response: {result}")
        job_status = sjs_status_mapper(result.get('status'))
        if job_status not in [JobStatus.cancelled, JobStatus.finished]:
            raise ValueError(f"Invalid job status {result.get('status')}")
        return job_status
