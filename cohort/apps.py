from django.apps import AppConfig, apps


class CohortConfig(AppConfig):
    name = 'cohort'

    if apps.is_installed("cohort_job_server"):
        from cohort_job_server.apps import CohortJobServerConfig
        COHORT_OPERATORS = CohortJobServerConfig.COHORT_OPERATORS
    else:
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
