from cohort.crb.cohort_requests.abstract_cohort_request import AbstractCohortRequest
from cohort.crb.enums import Mode
from cohort.crb.fhir_request import FhirRequest
from cohort.crb.source_population import SourcePopulation


class CohortCountAll(AbstractCohortRequest):
    def __init__(self, *args, **kwargs):
        super().__init__(mode=Mode.COUNT_ALL, *args, **kwargs)

    def action(self, fhir_request: FhirRequest) -> str:
        fhir_request.source_population = SourcePopulation(...)
        request = self.create_request(fhir_request)
        return self.sjs_client.count(request)
