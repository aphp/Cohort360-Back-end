from cohort.crb.cohort_requests.abstract_cohort_request import AbstractCohortRequest
from cohort.crb.enums import Mode
from cohort.crb.fhir_request import FhirRequest


class CohortCount(AbstractCohortRequest):
    def __init__(self, *args, **kwargs):
        super().__init__(mode=Mode.COUNT, *args, **kwargs)

    def action(self, fhir_request: FhirRequest) -> str:
        request = self.create_request(fhir_request)
        return self.sjs_client.count(request)
