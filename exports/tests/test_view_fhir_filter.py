from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from admin_cohort.tests.tests_tools import new_user_and_profile
from cohort.models import FhirFilter
from cohort.serializers import FhirFilterSerializer

User = get_user_model()


class FhirFilterViewSetTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user, _ = new_user_and_profile()

        # Create objects for user
        self.filter1 = FhirFilter.objects.create(
            owner=self.user, name="Test1", fhir_resource="Resource1",
            filter='{"gender": "male"}', auto_generated=False, identifying=False
        )
        self.filter2 = FhirFilter.objects.create(
            owner=self.user, name="Test2", fhir_resource="Resource2",
            filter='{"code": "1234"}', auto_generated=False, identifying=True
        )
        self.filter3 = FhirFilter.objects.create(
            owner=self.user, name="Test3", fhir_resource="Resource3",
            filter='{"some-field": "value"}', auto_generated=False, identifying=False
        )

        # This one shouldn't appear (auto_generated=True)
        FhirFilter.objects.create(
            owner=self.user, name="Auto", fhir_resource="AllergyIntolerance",
            filter='{"clinicalStatus": "active"}', auto_generated=True, identifying=False
        )

        self.client.force_authenticate(user=self.user)

    def test_list_identifying_filters(self):
        response = self.client.get("/exports/fhir-filters/?identifying=true")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        filters = FhirFilter.objects.filter(
            owner=self.user,
            auto_generated=False,
            identifying=True
        )
        serializer = FhirFilterSerializer(filters, many=True)
        self.assertEqual(response.json().get("results"), serializer.data)

    def test_list_non_identifying_filters(self):
        response = self.client.get("/exports/fhir-filters/?identifying=false")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        filters = FhirFilter.objects.filter(
            owner=self.user,
            auto_generated=False,
            identifying=False
        )
        serializer = FhirFilterSerializer(filters, many=True)
        self.assertEqual(response.json().get("results"), serializer.data)

    def test_list_all_filters(self):
        response = self.client.get("/exports/fhir-filters/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        filters = FhirFilter.objects.filter(
            owner=self.user,
            auto_generated=False,
        )
        serializer = FhirFilterSerializer(filters, many=True)
        self.assertEqual(response.json().get("results"), serializer.data)

    def test_unauthenticated_access_denied(self):
        self.client.force_authenticate(user=None)
        response = self.client.get("/exports/fhir-filters/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
