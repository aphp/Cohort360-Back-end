from django.apps import AppConfig
from django.conf import settings


class CohortOperatorsConfig(AppConfig):
    name = 'cohort_operators'

    def ready(self):
        settings.COHORT_OPERATORS = [
            {
                "TYPE": "count",
                "OPERATOR_CLASS": "cohort_operators.job_server_operators.CohortCountOperator"
            },
            {
                "TYPE": "create",
                "OPERATOR_CLASS": "cohort_operators.job_server_operators.CohortCreateOperator"
            }
        ]
        settings.JOB_SERVER_API_CONF = {}
