from django.apps import AppConfig, apps


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

    def ready(self):
        if apps.is_installed("cohort_job_server"):
            from cohort_job_server.apps import CohortJobServerConfig
            self.COHORT_OPERATORS = CohortJobServerConfig.COHORT_OPERATORS
