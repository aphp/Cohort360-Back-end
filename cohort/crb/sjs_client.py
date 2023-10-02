from __future__ import annotations

import json
from typing import TYPE_CHECKING

import requests
from requests import Response

from admin_cohort.settings import SJS_URL

if TYPE_CHECKING:
    from cohort.crb.schemas import CohortQuery, SparkJobObject


class SjsClient:
    APP_NAME = "omop-spark-job"
    url = SJS_URL

    # todo: remove this dependency by refactoring the SJS scala project and removing those class paths requirements
    COUNT_CLASSPATH = "fr.aphp.id.eds.requester.CountQuery"
    CREATE_CLASSPATH = "fr.aphp.id.eds.requester.CreateQuery"
    CONTEXT = "shared"

    def count(self, input_payload: str) -> tuple[Response, dict]:
        params = {
            'appName': self.APP_NAME,
            'classPath': self.COUNT_CLASSPATH,
            'context': self.CONTEXT
        }

        resp = requests.post(f"{self.url}/jobs", params=params, data=input_payload)
        resp.raise_for_status()
        result = resp.json()
        return resp, result

    def create(self, input_payload: str) -> tuple[Response, dict]:
        params = {
            'appName': self.APP_NAME,
            'classPath': self.CREATE_CLASSPATH,
            'context': self.CONTEXT,
            'sync': 'false'
        }

        resp = requests.post(f"{self.url}/jobs", params=params, data=input_payload)
        resp.raise_for_status()
        return resp, resp.json()

    def delete(self, job_id: str) -> str:
        resp = requests.delete(f"{self.url}/jobs/{job_id}")
        resp.raise_for_status()
        return resp.text


def replace_pattern(text: str, replacements: list[tuple[str, str]]) -> str:
    for pattern, replacement in replacements:
        text = text.replace(pattern, replacement)
    return text


def format_syntax(request: CohortQuery) -> str:
    json_data = request.model_dump_json(by_alias=True, exclude_none=True)
    replacements = [('"["All"]"', '"all"'), ('"[true]"', 'true'), ('"[false]"', 'false')]
    formatted_json = replace_pattern(json_data, replacements)
    return json.dumps(formatted_json)


def format_spark_job_request_for_sjs(spark_job_request: SparkJobObject) -> str:
    return str(
        f"input.cohortDefinitionName = {spark_job_request.cohort_definition_name},"
        f"input.cohortDefinitionSyntax = {format_syntax(spark_job_request.cohort_definition_syntax)},"
        f"input.ownerEntityId = {spark_job_request.owner_entity_id},"
        f"input.mode = {spark_job_request.mode},"
        f"input.cohortUuid = {spark_job_request.cohort_definition_syntax.cohort_uuid}"
    )
