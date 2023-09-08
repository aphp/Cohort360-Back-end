from accesses.conf_perimeters import CareSite
from cohort.crb.cohort_requests.abstract_cohort_request import AbstractCohortRequest
from cohort.crb.enums import Mode
from cohort.crb.fhir_request import FhirRequest
from cohort.crb.source_population import SourcePopulation


def fetch_aphp_care_site_id() -> int:
    care_site: CareSite = CareSite.objects.first()
    return care_site.cohort_id


class CohortCountAll(AbstractCohortRequest):
    def __init__(self, *args, **kwargs):
        super().__init__(mode=Mode.COUNT_ALL, *args, **kwargs)

    def action(self, fhir_request: FhirRequest) -> str:
        cohort_id = fetch_aphp_care_site_id()
        print(cohort_id)
        fhir_request.source_population = SourcePopulation(care_site_cohort_list=[cohort_id])
        request = self.create_request(fhir_request)
        return self.sjs_client.count(request)
