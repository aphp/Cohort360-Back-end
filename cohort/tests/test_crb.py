from cohort.crb import CRBFactory, CohortQueryBuilder, FhirRequest, SourcePopulation


class TestCRB:
    def test_count(self):
        cohort_query_builder = CohortQueryBuilder("user1")
        crb = CRBFactory(cohort_query_builder)
        cohort_count = crb.create_cohort_count()
        fhir_request = FhirRequest(source_population=SourcePopulation([]))
        count = cohort_count.request_to_sjs(fhir_request)
        ...
