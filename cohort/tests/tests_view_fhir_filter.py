import pytest
from django.db import IntegrityError
from django.urls import reverse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.test import force_authenticate

from admin_cohort.models import User
from cohort.models import FhirFilter
from cohort.tests.cohort_app_tests import CohortAppTests
from cohort.views.fhir_filter import FhirFilterViewSet


class TestFhirFilterAPI(CohortAppTests):
    list_view = FhirFilterViewSet.as_view({'get': 'list'})
    post_view = FhirFilterViewSet.as_view({'post': 'create'})
    patch_view = FhirFilterViewSet.as_view({'patch': 'partial_update'})

    def test_always_true(self):
        assert True

    def test_url_reverse(self):
        url = reverse("cohort:fhir-filters-list")
        assert url == "/cohort/fhir-filters/"

    def test_list_route_callable(self):
        url = reverse("cohort:fhir-filters-list")
        request = self.factory.get(url)
        force_authenticate(request, self.user1)
        response: Response = self.__class__.list_view(request)
        assert response.status_code == status.HTTP_200_OK

    def test_list_count_zero_when_empty(self):
        url = reverse("cohort:fhir-filters-list")
        request = self.factory.get(url)
        force_authenticate(request, self.user1)
        response: Response = self.__class__.list_view(request)
        assert response.data.get("count") == 0

    def test_create_fhir_filter(self):
        url = reverse("cohort:fhir-filters-list")
        user = User.objects.first()
        data = {
            'fhir_resource': 'Patient',
            'fhir_version': '1.0.0',
            'filter_name': 'test_filter',
            'fhir_filter': '{"some": "filter"}',
            'owner': user.pk
        }
        request = self.factory.post(url, data=data, format='json')
        force_authenticate(request, self.user1)
        response: Response = self.__class__.post_view(request)
        assert response.status_code == status.HTTP_201_CREATED
        assert FhirFilter.objects.count() == 1
        fhir_object = FhirFilter.objects.get()
        assert fhir_object.owner.pk == user.pk
        assert fhir_object.fhir_version == '1.0.0'
        assert fhir_object.filter_name == 'test_filter'

    def test_edit_filter_name(self):
        # Create a new FhirFilter instance
        fhir_filter = FhirFilter.objects.create(
            fhir_resource='Patient',
            fhir_version='1.0.0',
            filter_name='original_name',
            fhir_filter='{"some": "filter"}',
            owner=User.objects.first()
        )

        # Edit the filter_name field
        new_filter_name = 'new_name'
        url = reverse("cohort:fhir-filters-detail", args=[fhir_filter.pk])
        request = self.factory.patch(url, data={'filter_name': new_filter_name}, format='json')
        force_authenticate(request, self.user1)
        response: Response = self.__class__.patch_view(request, pk=fhir_filter.pk)
        assert response.status_code == status.HTTP_200_OK
        fhir_filter.refresh_from_db()
        assert fhir_filter.filter_name == new_filter_name

    def test_edit_filter_name_only_modifies_name(self):
        user = User.objects.first()
        kwargs = {
            'fhir_resource': 'Patient', 'fhir_version': '1.0.0', 'filter_name': 'original_name',
            'fhir_filter': '{"some": "filter"}', 'owner': user
        }
        fhir_filter = FhirFilter.objects.create(**kwargs)
        url = reverse("cohort:fhir-filters-detail", args=[fhir_filter.pk])
        request = self.factory.patch(url, data={'filter_name': 'new_name'}, format='json')
        force_authenticate(request, self.user1)
        self.__class__.patch_view(request, pk=fhir_filter.pk)
        fhir_filter.refresh_from_db()
        assert fhir_filter.filter_name == 'new_name'
        assert fhir_filter.fhir_resource == kwargs['fhir_resource']
        assert fhir_filter.fhir_version == kwargs['fhir_version']
        assert fhir_filter.fhir_filter == kwargs['fhir_filter']
        assert fhir_filter.owner == kwargs['owner']

    def test_uniqueness_same_object(self):
        user = User.objects.first()
        kwargs = {
            'fhir_resource': 'Patient', 'fhir_version': '1.0.0', 'filter_name': 'original_name',
            'fhir_filter': '{"some": "filter"}', 'owner': user
        }
        FhirFilter.objects.create(**kwargs)
        with pytest.raises(IntegrityError):
            FhirFilter.objects.create(**kwargs)

