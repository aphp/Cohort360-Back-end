import datetime
from random import randint

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, DataError
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
    recent_list_view = FhirFilterViewSet.as_view({'get': 'recent_filters'})
    lookup_field = "uuid"

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

    def test_create_filter(self):
        url = reverse("cohort:fhir-filters-list")
        user = User.objects.first()
        data = {
            'fhir_resource': 'Patient',
            'fhir_version': '1.0.0',
            'name': 'test_filter',
            'filter': '{"some": "filter"}',
        }
        request = self.factory.post(url, data=data, format='json')
        force_authenticate(request, user)
        response: Response = self.__class__.post_view(request)
        assert response.status_code == status.HTTP_201_CREATED
        assert FhirFilter.objects.count() == 1
        fhir_object = FhirFilter.objects.get()
        assert fhir_object.owner.pk == user.pk
        assert fhir_object.fhir_version == '1.0.0'
        assert fhir_object.name == 'test_filter'

    def test_edit_name(self):
        # Create a new FhirFilter instance
        fhir_filter = FhirFilter.objects.create(
            fhir_resource='Patient',
            fhir_version='1.0.0',
            name='original_name',
            filter='{"some": "filter"}',
            owner=self.user1)

        # Edit the name field
        new_name = 'new_name'
        url = reverse("cohort:fhir-filters-detail", args=[fhir_filter.uuid])
        request = self.factory.patch(url, data={'name': new_name}, format='json')
        force_authenticate(request, self.user1)
        response: Response = self.__class__.patch_view(request, uuid=fhir_filter.uuid)
        assert response.status_code == status.HTTP_200_OK
        fhir_filter.refresh_from_db()
        assert fhir_filter.name == new_name

    def test_edit_name_only_modifies_name(self):
        user = User.objects.first()
        kwargs = {
            'fhir_resource': 'Patient', 'fhir_version': '1.0.0', 'name': 'original_name',
            'filter': '{"some": "filter"}', 'owner': user
        }
        fhir_filter = FhirFilter.objects.create(**kwargs)
        url = reverse("cohort:fhir-filters-detail", args=[fhir_filter.pk])
        request = self.factory.patch(url, data={'name': 'new_name'}, format='json')
        force_authenticate(request, user)
        self.__class__.patch_view(request, uuid=fhir_filter.uuid)
        fhir_filter.refresh_from_db()
        assert fhir_filter.name == 'new_name'
        assert fhir_filter.fhir_resource == kwargs['fhir_resource']
        assert fhir_filter.fhir_version == kwargs['fhir_version']
        assert fhir_filter.filter == kwargs['filter']
        assert fhir_filter.owner == kwargs['owner']

    def test_uniqueness_for_non_deleted_filters(self):
        user = User.objects.first()
        data = {'fhir_resource': 'Patient',
                'name': 'name',
                'owner': user,
                'fhir_version': '1.0.0',
                'filter': '{"some": "filter"}',
                }
        FhirFilter.objects.create(**data)
        with pytest.raises(IntegrityError):
            FhirFilter.objects.create(**data)

    def test_uniqueness_for_deleted_filters(self):
        user = User.objects.first()
        data = {'fhir_resource': 'Patient',
                'name': 'name',
                'owner': user,
                'fhir_version': '1.1.0',
                'filter': '{"some": "filter"}',
                }
        f = FhirFilter.objects.create(**data)
        f.delete()
        assert f.deleted is not None, "Error: Filter was not deleted"
        try:
            FhirFilter.objects.create(**data)
        except IntegrityError:
            pytest.fail("Unexpected error: creation should work as the 1st Filter is deleted")

    def test_hundred_of_filters_no_api(self):
        user = User.objects.first()
        loops = randint(100, 600)
        for i in range(loops):
            FhirFilter.objects.create(
                fhir_resource=f"res {i}", name="name", owner=user,
                filter='{"some": "filter"}', fhir_version='1.0.0'
            )
        assert FhirFilter.objects.count() == loops

    def test_hundred_of_filters_api_call(self):
        user = User.objects.first()
        loops = randint(100, 600)
        url = reverse("cohort:fhir-filters-list")
        for i in range(loops):
            data = {
                'fhir_resource': f'res {i}',
                'fhir_version': '1.0.0',
                'name': 'test_filter',
                'filter': '{"some": "filter"}'
            }
            request = self.factory.post(url, data=data, format='json')
            force_authenticate(request, user)
            self.__class__.post_view(request)

        count_url = reverse("cohort:fhir-filters-list")
        count_request = self.factory.get(count_url)
        force_authenticate(count_request, user)
        response: Response = self.__class__.list_view(count_request)
        assert FhirFilter.objects.count() == loops == response.data.get("count")

    def test_name_minimal_length(self):
        user = User.objects.first()
        FhirFilter.objects.create(
            fhir_resource="Resource 1", name="x" * 2, owner=user,
            filter='{"some": "filter"}', fhir_version='1.0.0'
        )
        assert FhirFilter.objects.count() == 1

    def test_name_max_length(self):
        user = User.objects.first()
        FhirFilter.objects.create(
            fhir_resource="Resource 1", name="x" * 50, owner=user,
            filter='{"some": "filter"}', fhir_version='1.0.0'
        )
        assert FhirFilter.objects.count() == 1

    def test_name_max_length_plus_one(self):
        user = User.objects.first()
        with pytest.raises(DataError):
            FhirFilter.objects.create(
                fhir_resource="Resource 1", name="x" * 51, owner=user,
                filter='{"some": "filter"}', fhir_version='1.0.0'
            )

    def test_name_min_length_minus_one(self):
        user = User.objects.first()
        with pytest.raises(ValidationError):
            f = FhirFilter.objects.create(
                fhir_resource="Resource 1", name="x" * 1, owner=user,
                filter='{"some": "filter"}', fhir_version='1.0.0'
            )
            f.full_clean()  # needed because of a validator check, # todo: abstract implementation detail for the test

    def test_null_resource(self):
        with pytest.raises(IntegrityError):
            FhirFilter.objects.create(
                fhir_resource=None, name="name of filter", owner=User.objects.first(),
                filter='{"some": "filter"}', fhir_version='1.0.0'
            )

    def test_null_name(self):
        with pytest.raises(IntegrityError):
            FhirFilter.objects.create(
                fhir_resource="Resource 1", name=None, owner=User.objects.first(),
                filter='{"some": "filter"}', fhir_version='1.0.0'
            )

    def test_null_user(self):
        with pytest.raises(IntegrityError):
            FhirFilter.objects.create(
                fhir_resource="Resource 1", name="name of filter", owner=None,
                filter='{"some": "filter"}', fhir_version='1.0.0'
            )

    def test_null_filter(self):

        with pytest.raises(IntegrityError):
            FhirFilter.objects.create(
                fhir_resource="Resource 1", name="name of filter", owner=User.objects.first(),
                filter=None, fhir_version='1.0.0'
            )

    def test_null_version(self):
        with pytest.raises(IntegrityError):
            FhirFilter.objects.create(
                fhir_resource="Resource 1", name="name of filter", owner=User.objects.first(),
                filter='{"some": "filter"}', fhir_version=None
            )

    # def test_order_by_recent_date(self):
    #     # Create FhirFilter instances with different created_at values
    #     user = User.objects.first()
    #     FhirFilter.objects.create(
    #         fhir_resource='Resource 1', name='Filter 1', filter='{"some": "filter"}', owner=user,
    #         fhir_version="1.0.0"
    #     )
    #     FhirFilter.objects.create(
    #         fhir_resource='Resource 2', name='Filter 2', filter='{"some": "filter"}', owner=user,
    #         fhir_version="1.0.0"
    #     )
    #     FhirFilter.objects.create(
    #         fhir_resource='Resource 3', name='Filter 3', filter='{"some": "filter"}', owner=user,
    #         fhir_version="1.0.0"
    #     )
    #
    #     url = reverse("cohort:fhir-filters-recent-filters")
    #     request = self.factory.get(url)
    #     force_authenticate(request, user)
    #     response: Response = self.__class__.recent_list_view(request)
    #
    #     created_dates = [f['created_at'] for f in response.data]
    #     assert len(created_dates) == 3
    #     assert created_dates == sorted(created_dates, reverse=True)  # dates are in ISO 8601 which makes this possible
    #
    # def test_order_by_recent_date_random_dates(self):
    #     # Create FhirFilter instances with different created_at values
    #     user = User.objects.first()
    #     for i in range(100):
    #         f = FhirFilter.objects.create(
    #             fhir_resource=f"res {i}", name="name", owner=user,
    #             filter='{"some": "filter"}', fhir_version='1.0.0'
    #         )
    #         f.created_at = datetime.now() - timedelta(weeks=randint(0, 52 * 10))
    #         f.save()
    #
    #     url = reverse("cohort:fhir-filters-recent-filters")
    #     request = self.factory.get(url, user=user)
    #     force_authenticate(request, user)
    #     response: Response = self.__class__.recent_list_view(request)
    #
    #     created_dates = [f['created_at'] for f in response.data]
    #     assert len(created_dates) == 100
    #     assert created_dates == sorted(created_dates, reverse=True)  # dates are in ISO 8601 which makes this possible
