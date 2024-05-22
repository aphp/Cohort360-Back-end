from django.apps import AppConfig
from django.conf import settings


class CohortOperatorsConfig(AppConfig):
    name = 'cohort_operators'

    def ready(self):
        settings.COHORT_OPERATORS = [
            {
                "TYPE": "count",
                "OPERATOR_CLASS": "cohort_operators.cohort_counter.CohortCounter"
            },
            {
                "TYPE": "create",
                "OPERATOR_CLASS": "cohort_operators.cohort_creator.CohortCreator"
            }
        ]
        settings.JOB_SERVER_API_CONF = {}
