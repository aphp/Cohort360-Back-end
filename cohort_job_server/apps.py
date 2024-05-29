from django.apps import AppConfig
from django.conf import settings


class CohortJobServerConfig(AppConfig):
    name = 'cohort_job_server'

    def ready(self):
        settings.COHORT_OPERATORS = [
            {
                "TYPE": "count",
                "OPERATOR_CLASS": "cohort_job_server.cohort_counter.CohortCountOperator"
            },
            {
                "TYPE": "create",
                "OPERATOR_CLASS": "cohort_job_server.cohort_creator.CohortCreateOperator"
            }
        ]
        settings.JOB_SERVER_API_CONF = {}
