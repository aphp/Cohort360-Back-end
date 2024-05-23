from django.apps import AppConfig
from django.conf import settings


class CohortConfig(AppConfig):
    name = 'cohort'

    def ready(self):

        settings.COHORT_OPERATORS = getattr(settings, "COHORT_OPERATORS", [
            {
                "TYPE": "count",
                "OPERATOR_CLASS": "cohort.services.cohort_operators.DefaultCohortCount"
            },
            {
                "TYPE": "create",
                "OPERATOR_CLASS": "cohort.services.cohort_operators.DefaultCohortCreator"
            }
        ])
