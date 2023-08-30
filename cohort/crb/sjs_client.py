import json
from dataclasses import asdict

import requests

from admin_cohort.settings import SJS_URL
from cohort.crb.spark_job_object import SparkJobObject


class SjsClient:
    app_name = "omop-spark-job"
    url = SJS_URL

    # todo: remove this dependency by refactoring the SJS scala project and removing those class paths requirements
    count_classpath = "fr.aphp.id.eds.requester.CountQuery"
    create_classpath = "fr.aphp.id.eds.requester.CreateQuery"

    def count(self, request: str):
        resp = requests.post(url=f"{self.url}/jobs",
                             params={'appName': self.app_name},
                             json=request
                             )
        resp.raise_for_status()
        result = resp.json()
        return resp, result

    def create(self, request):
        ...


def format_spark_job_request_for_sjs(spark_job_request: SparkJobObject) -> str:
    res = json.dumps(asdict(spark_job_request))
    res = (
        res.replace('["All"]', '"all"')
        .replace('[true]', 'true')
        .replace('[false]', 'false')
    )
    res = json.dumps(res)
    return (
        f"input.cohortDefinitionName = {spark_job_request.cohort_definition_name},"
        f"input.cohortDefinitionSyntax = \"{res}\","
        f"input.ownerEntityId = {spark_job_request.owner_entity_id},"
        f"input.mode = {spark_job_request.mode},"
        f"input.cohortUuid = {spark_job_request.cohort_definition_syntax.cohort_uuid}"
    )
