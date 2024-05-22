from cohort.models import CohortResult


class DefaultCountOperator:

    def launch_global_estimate(self, cohort: CohortResult, request):
        raise NotImplementedError()


class DefaultCreateOperator:
    ...
