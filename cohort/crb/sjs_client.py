import requests

from admin_cohort.settings import SJS_URL
from cohort.crb.spark_job_object import SparkJobObject


class SjsClient:
    APP_NAME = "omop-spark-job"
    url = SJS_URL

    # todo: remove this dependency by refactoring the SJS scala project and removing those class paths requirements
    COUNT_CLASSPATH = "fr.aphp.id.eds.requester.CountQuery"
    CREATE_CLASSPATH = "fr.aphp.id.eds.requester.CreateQuery"
    CONTEXT = "shared"

    def count(self, request):
        params = {
            'appName': self.APP_NAME,
            'classPath': self.COUNT_CLASSPATH,
            'context': self.CONTEXT
        }

        resp = requests.post(f"{self.url}/jobs", params=params, json=request)
        resp.raise_for_status()
        result = resp.json()
        return resp, result

    def create(self, request):
        params = {
            'appName': self.APP_NAME,
            'classPath': self.CREATE_CLASSPATH,
            'context': self.CONTEXT,
            'sync': 'false'
        }

        resp = requests.post(f"{self.url}/jobs", params=params, json=request)
        resp.raise_for_status()
        result = resp.json()
        return resp, result

    def delete(self, job_id: str) -> str:
        resp = requests.delete(f"{self.url}/jobs/{job_id}")
        resp.raise_for_status()
        return resp.text


def format_spark_job_request_for_sjs(spark_job_request: SparkJobObject) -> str:
    # a = asdict(spark_job_request.cohort_definition_syntax)
    # res = json.dumps(a)
    # res = (
    #     res.replace('["All"]', '"all"')
    #     .replace('[true]', 'true')
    #     .replace('[false]', 'false')
    # )
    # print(res)
    # # res = json.dumps(res)
    return (
        f"input.cohortDefinitionName = {spark_job_request.cohort_definition_name},"
        # f"input.cohortDefinitionSyntax = \"{res}\","
        f"input.ownerEntityId = {spark_job_request.owner_entity_id},"
        f"input.mode = {spark_job_request.mode},"
        f"input.cohortUuid = {spark_job_request.cohort_definition_syntax.cohort_uuid}"
    )
