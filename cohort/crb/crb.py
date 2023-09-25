from cohort.crb.cohort_requests.abstract_cohort_request import AbstractCohortRequest
from cohort.crb.fhir_request import FhirRequest


class CRB:
    def __init__(self, cohort_action: AbstractCohortRequest):
        self.cohort_action = cohort_action

    def request_to_sjs(self, fhir_request: FhirRequest) -> dict:
        return self.cohort_action.action(fhir_request)
