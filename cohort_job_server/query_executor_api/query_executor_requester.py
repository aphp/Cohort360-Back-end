import json
from typing import Type, Callable

from django.db.models import Model
from requests import HTTPError
from rest_framework import status

from admin_cohort.types import JobStatus
from admin_cohort.exceptions import MissingDataError
from cohort.models import CohortResult
from cohort_job_server.query_executor_api import BaseCohortRequest, CohortQuery, QueryExecutorClient, QueryExecutorResponse,\
    query_executor_status_mapper
from cohort_job_server.utils import _logger_err


LoggerType = Type[Callable[..., None]]


class QueryExecutorRequester:

    def launch_request(self, cohort_request: BaseCohortRequest) -> QueryExecutorResponse:
        _logger = cohort_request.log
        instance_id = cohort_request.instance_id
        json_query = cohort_request.json_query
        try:
            _logger(msg=f"Converting the json query: {json_query}")
            cohort_query = CohortQuery(instance_id=instance_id, **json.loads(json_query))
            response = cohort_request.launch(cohort_query)
        except Exception as e:
            _logger_err.error(f"Error sending request to Query Executor: {e}")
            response_data = {"success": False, "err_msg": str(e), "status": "ERROR"}
        else:
            response_data = {"success": True, **response.json()}
        response = QueryExecutorResponse(**response_data)
        _logger(msg=f"Received Query Executor response {response.__dict__}")
        if instance_id is not None and cohort_request.model is not None:
            self.update_request_instance(cohort_request.model, instance_id, response)
        _logger(msg=f"Done: {response.success and f'{cohort_request.model.__name__} updated' or response.err_msg}")
        return response

    @staticmethod
    def update_request_instance(instance_model: Model, instance_id: str, response: QueryExecutorResponse) -> None:
        instance = instance_model.objects.get(pk=instance_id)
        job_status = response.job_status
        if response.success:
            instance.request_job_id = response.job_id
            if instance_model is CohortResult:
                current_job_status = instance.request_job_status
                # At this point, current_job_status is either `pending` or `long_pending`
                # if `long_pending`, leave it as is. if `pending`, update it to job_status (`started`)
                if current_job_status == JobStatus.long_pending:
                    job_status = current_job_status
        else:
            instance.request_job_fail_msg = response.err_msg
        instance.request_job_status = job_status
        instance.save()

    @staticmethod
    def cancel_job(job_id: str) -> JobStatus:
        try:
            response = QueryExecutorClient().delete(job_id)
            result = response.json()
        except json.JSONDecodeError as e:
            raise ValueError(f"Error with response content: {str(e)}")
        if response.status_code == status.HTTP_403_FORBIDDEN:
            return JobStatus.finished
        if response.status_code != status.HTTP_200_OK:
            raise HTTPError(f"Cancel request failed: {response.status_code}: {result}")
        if 'status' not in result:
            raise MissingDataError(f"`status` is missing in response: {result}")
        job_status = query_executor_status_mapper(result.get('status'))
        if job_status not in [JobStatus.cancelled, JobStatus.finished]:
            raise ValueError(f"Invalid job status {result.get('status')}")
        return job_status
