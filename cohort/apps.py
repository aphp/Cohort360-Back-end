from django.apps import AppConfig
from django.conf import settings


class CohortConfig(AppConfig):
    name = 'cohort'

    COHORT_OPERATORS = [
        {
            "TYPE": "count",
            "OPERATOR_CLASS": "cohort.services.cohort_operators.DefaultCohortCounter"
        },
        {
            "TYPE": "create",
            "OPERATOR_CLASS": "cohort.services.cohort_operators.DefaultCohortCreator"
        }
    ]
    if "cohort_job_server" in settings.INSTALLED_APPS:
        from cohort_job_server.apps import CohortJobServerConfig
        COHORT_OPERATORS = CohortJobServerConfig.COHORT_OPERATORS
