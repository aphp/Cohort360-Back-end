from django.urls import reverse

from cohort.tests.cohort_app_tests import CohortAppTests
from rest_framework.test import force_authenticate

from cohort.views.fhir_filter import FhirFilterViewSet


class TestFhirFilterAPI(CohortAppTests):
    list_view = FhirFilterViewSet.as_view({'get': 'list'})

    def test_always_true(self):
        assert True

    def test_url_reverse(self):
        url = reverse("cohort:fhir-filters-list")
        assert url == "/cohort/fhir-filters/"

    def test_list_route_callable(self):
        url = reverse("cohort:fhir-filters-list")
        request = self.factory.get(url)
        force_authenticate(request, self.user1)
        response = self.__class__.list_view(request)
        assert response.status_code == 200
