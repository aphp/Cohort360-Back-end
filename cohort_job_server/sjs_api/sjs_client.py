from __future__ import annotations

import json
import logging
import os
from typing import TYPE_CHECKING

import requests
from requests import Response

if TYPE_CHECKING:
    from cohort_job_server.sjs_api import CohortQuery, SparkJobObject

_logger = logging.getLogger('info')


class SJSClient:
    APP_NAME = "omop-spark-job"

    # todo: remove this dependency by refactoring the SJS scala project and removing those class paths requirements
    COUNT_CLASSPATH = "fr.aphp.id.eds.requester.CountQuery"
    CREATE_CLASSPATH = "fr.aphp.id.eds.requester.CreateQuery"
    CONTEXT = "shared"

    def __init__(self):
        self.api_url = f"{os.environ.get('SJS_URL')}/jobs"

    def count(self, input_payload: str) -> Response:
        _logger.info(f"Count query payload: {input_payload}")
        params = {
            'appName': self.APP_NAME,
            'classPath': self.COUNT_CLASSPATH,
            'context': self.CONTEXT
        }
        return requests.post(self.api_url, params=params, data=input_payload)

    def create(self, input_payload: str) -> Response:
        params = {
            'appName': self.APP_NAME,
            'classPath': self.CREATE_CLASSPATH,
            'context': self.CONTEXT,
            'sync': 'false'
        }
        return requests.post(self.api_url, params=params, data=input_payload)

    def delete(self, job_id: str) -> Response:
        return requests.delete(f"{self.api_url}/{job_id}")


def replace_pattern(text: str, replacements: list[tuple[str, str]]) -> str:
    for pattern, replacement in replacements:
        text = text.replace(pattern, replacement)
    return text


def format_syntax(request: CohortQuery) -> str:
    json_data = request.model_dump_json(by_alias=True, exclude_none=True)
    replacements = [('["All"]', '"all"'), ('[true]', 'true'), ('[false]', 'false')]
    formatted_json = replace_pattern(json_data, replacements)
    return json.dumps(formatted_json)


def format_spark_job_request_for_sjs(spark_job_request: SparkJobObject) -> str:
    callback_path = spark_job_request.callbackPath
    request_input = str(f"input.cohortDefinitionName = {spark_job_request.cohort_definition_name},"
                        f"input.cohortDefinitionSyntax = {format_syntax(spark_job_request.cohort_definition_syntax)},"
                        f"input.ownerEntityId = {spark_job_request.owner_entity_id},"
                        f"input.mode = {spark_job_request.mode},"
                        f"input.cohortUuid = {spark_job_request.cohort_definition_syntax.instance_id}")
    if callback_path:
        request_input += f",input.callbackPath = {callback_path}"
    return request_input
