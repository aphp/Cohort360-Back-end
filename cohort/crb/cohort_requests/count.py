from cohort.crb.cohort_requests.abstract_cohort_request import AbstractCohortRequest
from cohort.crb.enums import Mode
from cohort.crb.cohort_query import CohortQuery


class CohortCount(AbstractCohortRequest):
    def __init__(self, *args, **kwargs):
        super().__init__(mode=Mode.COUNT, *args, **kwargs)

    def action(self, fhir_request: CohortQuery) -> str:
        request = self.create_request(fhir_request)
        return self.sjs_client.count(request)
