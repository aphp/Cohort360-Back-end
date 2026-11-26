from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

import requests
from django.conf import settings
from requests import Response

from admin_cohort.http_timeout import HTTP_REQUEST_TIMEOUT
from admin_cohort.middleware.context_request_middleware import get_trace_id

if TYPE_CHECKING:
    from cohort_job_server.query_executor_api import CohortQuery, SparkJobObject


class QueryExecutorClient:
    def __init__(self):
        self.api_url = f"{os.environ.get('QUERY_EXECUTOR_URL')}/jobs"

    @staticmethod
    def get_headers(auth_headers: dict | None) -> dict:
        # The SJS checks the token itself (user rights, pseudo), so the caller's token is forwarded as is
        return {**(auth_headers or {}), settings.TRACE_ID_HEADER: get_trace_id()}

    def submit(self, job_input: dict, auth_headers: dict | None = None) -> Response:
        return requests.post(self.api_url, json=job_input, headers=self.get_headers(auth_headers), timeout=HTTP_REQUEST_TIMEOUT)

    def delete(self, job_id: str, auth_headers: dict | None = None) -> Response:
        return requests.delete(f"{self.api_url}/{job_id}", headers=self.get_headers(auth_headers), timeout=HTTP_REQUEST_TIMEOUT)


def replace_pattern(text: str, replacements: list[tuple[str, str]]) -> str:
    for pattern, replacement in replacements:
        text = text.replace(pattern, replacement)
    return text


def format_syntax(request: CohortQuery) -> str:
    json_data = request.model_dump_json(by_alias=True, exclude_none=True)
    replacements = [('["All"]', '"all"'), ("[true]", "true"), ("[false]", "false")]
    return replace_pattern(json_data, replacements)


def format_spark_job_request_for_query_executor(spark_job_request: SparkJobObject) -> dict:
    cohort_query = spark_job_request.cohort_definition_syntax
    job_input: dict[str, Any] = {
        "cohortDefinitionName": spark_job_request.cohort_definition_name,
        "cohortDefinitionSyntax": format_syntax(cohort_query),
        "mode": spark_job_request.mode,
    }
    if spark_job_request.owner_entity_id:
        job_input["ownerEntityId"] = spark_job_request.owner_entity_id
    if cohort_query.instance_id:
        job_input["cohortUuid"] = str(cohort_query.instance_id)
    if spark_job_request.callback_path:
        job_input["callbackPath"] = spark_job_request.callback_path
    if spark_job_request.mode_options is not None:
        job_input["modeOptions"] = spark_job_request.mode_options.model_dump(exclude_none=True)
    return {"input": job_input}
