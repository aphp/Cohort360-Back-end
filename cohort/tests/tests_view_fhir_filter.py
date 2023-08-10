from django.urls import reverse

from cohort.tests.cohort_app_tests import CohortAppTests


class TestFhirFilterAPI(CohortAppTests):

    def test_always_true(self):
        assert True

    def test_url_reverse(self):
        url = reverse("cohort:fhir-filters-list")
        assert url == "/cohort/fhir-filters/"
