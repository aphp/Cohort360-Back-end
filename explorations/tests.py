from datetime import timedelta
from unittest import mock

from celery.result import AsyncResult
from django.urls import reverse
from django.utils import timezone
from django.utils.datetime_safe import datetime
from rest_framework import status
from rest_framework.test import force_authenticate

from cohort_back.FhirAPi import FhirValidateResponse, FhirCountResponse, FhirCohortResponse
from cohort_back.tests import BaseTests
from explorations.models import Request, RequestQuerySnapshot, DatedMeasure, CohortResult, PENDING_REQUEST_STATUS, \
    FINISHED_REQUEST_STATUS, FAILED_REQUEST_STATUS
from explorations.tasks import get_count_task, create_cohort_task
from explorations.views import RequestViewSet, RequestQuerySnapshotViewSet, DatedMeasureViewSet, CohortResultViewSet

EXPLORATIONS_URL = "/explorations"
REQUESTS_URL = f"{EXPLORATIONS_URL}/requests"
RQS_URL = f"{EXPLORATIONS_URL}/request-query-snapshots"
DATED_MEASURES_URL = f"{EXPLORATIONS_URL}/dated-measures"
COHORTS_URL = f"{EXPLORATIONS_URL}/cohorts"


# TODO : test for post save0 get saved, get last_modified,
# TODO : make test for create/get Request's Rqs, Rqs' dated_measure, Rqs' cohortresult
# TODO : prevent add rqs with previous not on active branch

# REQUESTS
class RequestsTests(BaseTests):
    def setUp(self):
        super(RequestsTests, self).setUp()
        self.user1_req1 = Request(
            owner=self.user1,
            name="Request 1",
            description=" Request 1 from user 1",
        )
        self.user1_req1.save()

        self.user2_req1 = Request(
            owner=self.user2,
            name="Request 1",
            description=" Request 1 from user 2",
        )
        self.user2_req1.save()

        self.retrieve_view = RequestViewSet.as_view({'get': 'retrieve'})
        self.create_view = RequestViewSet.as_view({'post': 'create'})
        self.delete_view = RequestViewSet.as_view({'delete': 'destroy'})
        self.update_view = RequestViewSet.as_view({'patch': 'partial_update'})


class RequestsGetTests(RequestsTests):
    def setUp(self):
        super(RequestsGetTests, self).setUp()
        self.retrieve_view

    def test_user_simple_get(self):
        # As a user, I can get a request I did
        request = self.factory.get(f'{REQUESTS_URL}')
        force_authenticate(request, self.user1)
        response = self.retrieve_view(request, uuid=self.user1_req1.uuid)
        response.render()
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        req_to_find = self.user1_req1
        self.check_get_response(response, req_to_find)

    def test_error_simple_get_not_owned(self):
        # As a user, I can't get a request user 2 created
        request = self.factory.get(f'{REQUESTS_URL}')
        force_authenticate(request, self.user2)
        response = self.retrieve_view(request, uuid=self.user1_req1.uuid)
        response.render()
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND, response.content)


class RequestsCreateTests(RequestsTests):
    def test_create_simple_request(self):
        # As a user, I can create a request
        request = self.factory.post(REQUESTS_URL, dict(
            name="Request 3",
            description="Request number 3",
        ), format='json')
        force_authenticate(request, self.user1)
        response = self.create_view(request)
        response.render()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.content)
        req = Request.objects.filter(
            name="Request 3",
            description="Request number 3",
            owner_id=self.user1.uuid).first()
        self.assertIsNotNone(req)

    def test_error_create_simple_request_with_other_owner(self):
        # As a user, I can create a request
        request = self.factory.post(REQUESTS_URL, dict(
            name="Request 3",
            description="Request number 3",
            owner_id=self.user2.uuid
        ), format='json')
        force_authenticate(request, self.user1)
        response = self.create_view(request)
        response.render()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.content)
        req = Request.objects.filter(
            name="Request 3",
            description="Request number 3").first()
        self.assertIsNone(req)


class RequestsDeleteTests(RequestsTests):
    def setUp(self):
        self.view = RequestViewSet.as_view({'delete': 'destroy'})
        return super(RequestsDeleteTests, self).setUp()

    def test_delete_request_as_owner(self):
        # As a user, I can delete a request I created
        request = self.factory.delete(REQUESTS_URL)
        force_authenticate(request, self.user1)
        response = self.delete_view(request, uuid=self.user1_req1.uuid)
        response.render()

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT, response.content)
        req = Request.objects.filter(
            uuid=self.user1_req1.uuid
        ).first()
        self.assertIsNone(req)

    def test_error_delete_request_as_not_owner(self):
        # As a user, I cannot delete another user's request
        request = self.factory.delete(REQUESTS_URL)
        force_authenticate(request, self.user2)
        response = self.delete_view(request, uuid=self.user1_req1.uuid)
        response.render()

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND, response.content)
        self.assertIsNotNone(Request.objects.filter(
            uuid=self.user1_req1.uuid
        ).first())


class RequestsUpdateTests(RequestsTests):
    def test_update_request_as_owner(self):
        # As a user, I can update a request I created
        request = self.factory.patch(REQUESTS_URL, dict(
            name="New name",
            description="New description",
        ), format='json')
        force_authenticate(request, self.user1)
        response = self.update_view(request, uuid=self.user1_req1.uuid)
        response.render()

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        req = Request.objects.get(uuid=self.user1_req1.uuid)
        self.assertEqual(req.name, "New name")
        self.assertEqual(req.description, "New description")

    def test_error_update_request_as_not_owner(self):
        # As a user, I cannot update another user's request
        request = self.factory.patch(REQUESTS_URL, dict(
            name="New name",
            description="New description",
        ), format='json')
        force_authenticate(request, self.user2)
        response = self.update_view(request, uuid=self.user1_req1.uuid)
        response.render()

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND, response.content)
        req = Request.objects.get(uuid=self.user1_req1.uuid)
        self.assertEqual(req.name, self.user1_req1.name)
        self.assertEqual(req.description, self.user1_req1.description)

    def test_error_update_request_forbidden_fields(self):
        # As a user, I cannot update some fields in a request I created
        request = self.factory.patch(REQUESTS_URL, dict(
            owner_id=self.user2.uuid,
        ), format='json')
        force_authenticate(request, self.user1)
        response = self.update_view(request, uuid=self.user1_req1.uuid)
        response.render()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.content)

        req = Request.objects.get(uuid=self.user1_req1.uuid)
        self.assertEqual(req.owner_id, self.user1_req1.owner_id)


# REQUEST_QUERY_SNAPSHOTS
class RqsTests(RequestsTests):
    def setUp(self):
        super(RqsTests, self).setUp()
        #          user1_snap1
        #           /       \
        # user1_b1_snap2  user1_b2_snap2 (active) (saved)
        #                         |
        #                 user1_b2_snap3 (active)

        self.user1_req2 = Request(
            owner=self.user1,
            name="Request 2",
            description=" Request 2 from user 1",
        )
        self.user1_req2.save()

        self.user1_req1_snap1 = RequestQuerySnapshot(
            owner=self.user1,
            request=self.user1_req1,
        )
        self.user1_req1_snap1.save()

        self.user1_req1_branch1_snap2 = RequestQuerySnapshot(
            owner=self.user1,
            request=self.user1_req1,
            previous_snapshot=self.user1_req1_snap1,
            serialized_query='{"perimeter": "Terra"}',
            is_active_branch=False,
        )
        self.user1_req1_branch1_snap2.save()

        self.user1_req1_branch2_snap2 = RequestQuerySnapshot(
            owner=self.user1,
            request=self.user1_req1,
            previous_snapshot=self.user1_req1_snap1,
            serialized_query='{"perimeter": "Hera"}',
            saved=True,
        )
        self.user1_req1_branch2_snap2.save()

        self.user1_req1_branch2_snap3 = RequestQuerySnapshot(
            owner=self.user1,
            request=self.user1_req1,
            previous_snapshot=self.user1_req1_snap1,
            serialized_query='{"perimeter": "Hera", "condition1": {}}',
        )
        self.user1_req1_branch2_snap3.save()

        self.user2_req1_snap1 = RequestQuerySnapshot(
            owner=self.user2,
            request=self.user2_req1,
        )
        self.user2_req1_snap1.save()

        self.retrieve_view = RequestQuerySnapshotViewSet.as_view({'get': 'retrieve'})
        self.list_view = RequestQuerySnapshotViewSet.as_view({'get': 'list'})
        self.create_view = RequestQuerySnapshotViewSet.as_view({'post': 'create'})
        self.delete_view = RequestQuerySnapshotViewSet.as_view({'delete': 'destroy'})
        self.update_view = RequestQuerySnapshotViewSet.as_view({'patch': 'update'})


class RqsGetTests(RqsTests):
    def test_rqs_simple_get(self):
        # As a user, I can get a rqs I did
        request = self.factory.get(f'{RQS_URL}')
        force_authenticate(request, self.user1)
        response = self.retrieve_view(request, uuid=self.user1_req1_snap1.uuid)
        response.render()
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        rqs_to_find = self.user1_req1_snap1
        self.check_get_response(response, rqs_to_find)

    def test_error_simple_get_wrong_owner(self):
        # As a user, I can't get a rqs user I don't own
        request = self.factory.get(f'{RQS_URL}')
        force_authenticate(request, self.user1)
        response = self.retrieve_view(request, uuid=self.user2_req1_snap1.uuid)
        response.render()
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND, response.content)

    def test_rest_get_list_from_request(self):
        # As a user, I can get the list of RQS from the Request they are bound to
        url = reverse(
            'explorations:request-request-query-snapshots-list',
            kwargs=dict(parent_lookup_request=self.user1_req1.uuid)
        )
        self.client.force_login(self.user1)
        response = self.client.get(url)
        response.render()

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        rqs_to_find = [self.user1_req1_snap1, self.user1_req1_branch1_snap2,
                       self.user1_req1_branch2_snap2, self.user1_req1_branch2_snap3]
        self.check_get_response(response, rqs_to_find)


class RqsCreateTests(RqsTests):
    @mock.patch('explorations.serializers.fhir_api')
    def test_create_rqs_after_another(self, mock_fhir_api):
        # As a user, I can create a rqs after one in the active branch of a request
        mock_fhir_api.post_validate_cohort.return_value = FhirValidateResponse(True)
        test_sq = '{"test": "success"}'

        request = self.factory.post(RQS_URL, dict(
            previous_snapshot_id=self.user1_req1_branch2_snap3.uuid,
            serialized_query=test_sq,
        ), format='json')
        force_authenticate(request, self.user1)
        response = self.create_view(request)
        response.render()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.content)
        rqs = RequestQuerySnapshot.objects.filter(
            serialized_query=test_sq,
            owner=self.user1,
            previous_snapshot=self.user1_req1_branch2_snap3,
            request=self.user1_req1
        ).first()
        self.assertIsNotNone(rqs)
        mock_fhir_api.post_validate_cohort.assert_called_once()

    @mock.patch('explorations.serializers.fhir_api')
    def test_error_create_unvalid_query(self, mock_fhir_api):
        # As a user, I can create a rqs after one in the active branch of a request
        mock_fhir_api.post_validate_cohort.return_value = FhirValidateResponse(False)
        test_sq = '{"test": "success"}'

        request = self.factory.post(RQS_URL, dict(
            previous_snapshot_id=self.user1_req1_branch2_snap3.uuid,
            serialized_query=test_sq,
        ), format='json')
        force_authenticate(request, self.user1)
        response = self.create_view(request)
        response.render()

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.content)
        rqs = RequestQuerySnapshot.objects.filter(
            owner=self.user1,
            serialized_query=test_sq,
            previous_snapshot=self.user1_req1_branch2_snap3,
            request=self.user1_req1
        ).first()
        self.assertIsNone(rqs)
        mock_fhir_api.post_validate_cohort.assert_called_once()

    @mock.patch('explorations.serializers.fhir_api')
    def test_create_rqs_on_users_empty_request(self, mock_fhir_api):
        # As a user, I can create a rqs for a request that has no rqs yet
        mock_fhir_api.post_validate_cohort.return_value = FhirValidateResponse(True)

        test_sq = '{"test": "success"}'
        request = self.factory.post(RQS_URL, dict(
            request_id=self.user1_req2.uuid,
            serialized_query=test_sq,
        ), format='json')
        force_authenticate(request, self.user1)
        response = self.create_view(request)
        response.render()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.content)
        rqs = RequestQuerySnapshot.objects.filter(
            serialized_query=test_sq,
            owner_id=self.user1.uuid,
            request_id=self.user1_req2.uuid,
            previous_snapshot_id=None
        ).first()
        self.assertIsNotNone(rqs)
        mock_fhir_api.post_validate_cohort.assert_called_once()

    @mock.patch('explorations.serializers.fhir_api')
    def test_rest_create_rqs_from_request(self, mock_fhir_api):
        # As a user, I can create a rqs for a request that has no rqs yet, from request's url
        mock_fhir_api.post_validate_cohort.return_value = FhirValidateResponse(True)
        test_sq = '{"test": "success"}'

        url = reverse(
            'explorations:request-request-query-snapshots-list',
            kwargs=dict(parent_lookup_request=self.user1_req2.uuid)
        )
        self.client.force_login(self.user1)
        response = self.client.post(url, data=dict(
            serialized_query=test_sq,
        ), format='json')
        response.render()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.content)
        rqs = RequestQuerySnapshot.objects.filter(
            serialized_query=test_sq,
            owner_id=self.user1.uuid,
            request_id=self.user1_req2.uuid,
            previous_snapshot_id=None
        ).first()
        self.assertIsNotNone(rqs)
        mock_fhir_api.post_validate_cohort.assert_called_once()

    @mock.patch('explorations.serializers.fhir_api')
    def test_rest_create_next_rqs(self, mock_fhir_api):
        # As a user, I can create a rqs after one in the active branch of a request, from previous rqs' url
        mock_fhir_api.post_validate_cohort.return_value = FhirValidateResponse(True)
        test_sq = '{"test": "success"}'
        url = reverse(
            'explorations:request-query-snapshot-next-snapshots-list',
            kwargs=dict(parent_lookup_previous_snapshot_id=self.user1_req1_branch2_snap3.uuid)
        )
        self.client.force_login(self.user1)
        response = self.client.post(url, data=dict(
            serialized_query=test_sq,
        ), format='json')
        response.render()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.content)
        rqs = RequestQuerySnapshot.objects.filter(
            owner=self.user1,
            previous_snapshot=self.user1_req1_branch2_snap3,
            request=self.user1_req1,
            serialized_query=test_sq,
        ).first()
        self.assertIsNotNone(rqs)
        mock_fhir_api.post_validate_cohort.assert_called_once()

    def test_error_create_rqs_with_forbidden_access(self):
        forbidden_sq = '{"test": "forbidden"}'

        # As a user, I cannot create a rqs specifying another user
        request = self.factory.post(RQS_URL, dict(
            previous_snapshot_id=self.user1_req1_branch2_snap3.uuid,
            owner_id=self.user2.uuid,
            serialized_query=forbidden_sq
        ), format='json')
        force_authenticate(request, self.user1)
        response = self.create_view(request)
        response.render()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.content)

        # As a user, I cannot create a rqs specifying a request not matching the prev_snapshot
        request = self.factory.post(RQS_URL, dict(
            previous_snapshot_id=self.user1_req1_branch2_snap3.uuid,
            request_id=self.user1_req2.uuid,
            serialized_query=forbidden_sq
        ), format='json')
        force_authenticate(request, self.user1)
        response = self.create_view(request)
        response.render()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.content)

        # As a user, I cannot create a rqs specifying another user as owner
        request = self.factory.post(RQS_URL, dict(
            previous_snapshot_id=self.user1_req1_branch2_snap3.uuid,
            owner_id=self.user2.uuid,
            serialized_query=forbidden_sq,
        ), format='json')
        force_authenticate(request, self.user1)
        response = self.create_view(request)
        response.render()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.content)

        # As a user, I cannot create a rqs specifying only a non-empty request
        request = self.factory.post(RQS_URL, dict(
            request_id=self.user1_req1_snap1.uuid,
            serialized_query=forbidden_sq
        ), format='json')
        force_authenticate(request, self.user1)
        response = self.create_view(request)
        response.render()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.content)

        self.assertIsNone(RequestQuerySnapshot.objects.filter(
            serialized_query=forbidden_sq
        ).first())

    def test_error_create_rqs_for_request_not_owned(self):
        # As a user, I cannot create a rqs specifying a prev_snapshot I don't own
        forbidden_sq = '{"test": "forbidden"}'
        request = self.factory.post(RQS_URL, dict(
            previous_snapshot_id=self.user2_req1_snap1.uuid,
            serialized_query=forbidden_sq
        ), format='json')
        force_authenticate(request, self.user1)
        response = self.create_view(request)
        response.render()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.content)

        self.assertIsNone(RequestQuerySnapshot.objects.filter(
            serialized_query=forbidden_sq
        ).first())


class RqsDeleteTests(RqsTests):
    def test_error_delete_rqs(self):
        # As a user, I cannot delete a rqs, even if I own it
        request = self.factory.delete(RQS_URL)
        force_authenticate(request, self.user1)
        response = self.delete_view(request, uuid=self.user1_req1_branch2_snap3.uuid)
        response.render()

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.content)
        self.assertIsNotNone(RequestQuerySnapshot.objects.filter(uuid=self.user1_req1_branch2_snap3.uuid).first())


class RqsUpdateTests(RqsTests):
    def test_error_update_rqs(self):
        # As a user, I cannot update a rqs, even if I own it
        request = self.factory.patch(RQS_URL, dict(
            serialized_query='{"test": "forbidden"}',
        ), format='json')
        force_authenticate(request, self.user1)
        response = self.update_view(request, uuid=self.user1_req1_branch2_snap3.uuid)
        response.render()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.content)

        rqs = RequestQuerySnapshot.objects.get(uuid=self.user1_req1_branch2_snap3.uuid)
        self.assertEqual(rqs.serialized_query, self.user1_req1_branch2_snap3.serialized_query)


# DATED_MEASURES
class DatedMeasuresTests(RqsTests):
    def setUp(self):
        super(DatedMeasuresTests, self).setUp()
        self.user1_req1_branch2_snap3_dm1 = DatedMeasure(
            owner=self.user1,
            request=self.user1_req1,
            request_query_snapshot=self.user1_req1_branch2_snap3,
            measure=10,
            fhir_datetime=datetime.now(tz=timezone.utc) + timedelta(days=-2)
        )
        self.user1_req1_branch2_snap3_dm1.save()

        self.user1_req1_branch2_snap3_dm2 = DatedMeasure(
            owner=self.user1,
            request=self.user1_req1,
            request_query_snapshot=self.user1_req1_branch2_snap3,
            measure=20,
            fhir_datetime=datetime.now(tz=timezone.utc) + timedelta(days=-1)
        )
        self.user1_req1_branch2_snap3_dm2.save()

        self.user2_req1_snap1_dm1 = DatedMeasure(
            owner=self.user2,
            request=self.user2_req1,
            request_query_snapshot=self.user2_req1_snap1,
            measure=20,
            fhir_datetime=datetime.now(tz=timezone.utc) + timedelta(days=-1)
        )
        self.user2_req1_snap1_dm1.save()

        self.list_view = DatedMeasureViewSet.as_view({'get': 'list'})
        self.retrieve_view = DatedMeasureViewSet.as_view({'get': 'retrieve'})
        self.create_view = DatedMeasureViewSet.as_view({'post': 'create'})
        self.delete_view = DatedMeasureViewSet.as_view({'delete': 'destroy'})
        self.update_view = DatedMeasureViewSet.as_view({'patch': 'partial_update'})


class DatedMeasuresGetTests(DatedMeasuresTests):
    def test_user_simple_get(self):
        # As a user, I can get a dated_measure I generated
        request = self.factory.get(f'{DATED_MEASURES_URL}')
        force_authenticate(request, self.user1)
        response = self.retrieve_view(request, uuid=self.user1_req1_branch2_snap3_dm1.uuid)
        response.render()
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        dm_to_find = self.user1_req1_branch2_snap3_dm1
        self.check_get_response(response, dm_to_find)

    def test_error_user_simple_get(self):
        # As a user, I can't get a dated_measure user 2 generated
        request = self.factory.get(f'{DATED_MEASURES_URL}')
        force_authenticate(request, self.user1)
        response = self.retrieve_view(request, uuid=self.user2_req1_snap1_dm1.uuid)
        response.render()
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND, response.content)

    def test_user_get_snapshot_list(self):
        # As a user, I can get a list of dated_measures generated from a Rqs I own
        request = self.factory.get(f'{DATED_MEASURES_URL}/?request_query_snapshot={self.user1_req1_branch2_snap3.uuid}')
        force_authenticate(request, self.user1)
        response = self.list_view(request)
        response.render()
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        dm_to_find = [self.user1_req1_branch2_snap3_dm1, self.user1_req1_branch2_snap3_dm2]
        self.check_get_response(response, dm_to_find)

    def test_rest_get_list_from_rqs(self):
        # As a user, I can get the list of RQS from the rqs they are bound to
        self.user1_req1_branch2_snap2_dm1 = DatedMeasure(
            owner=self.user1,
            request=self.user1_req1,
            request_query_snapshot=self.user1_req1_branch2_snap2,
            measure=10,
            fhir_datetime=datetime.now(tz=timezone.utc) + timedelta(days=-2)
        )
        self.user1_req1_branch2_snap2_dm1.save()
        url = reverse(
            'explorations:request-query-snapshot-dated-measures-list',
            kwargs=dict(parent_lookup_request_query_snapshot=self.user1_req1_branch2_snap3.uuid)
        )
        self.client.force_login(self.user1)
        response = self.client.get(url)
        response.render()
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        rqs_to_find = [self.user1_req1_branch2_snap3_dm1, self.user1_req1_branch2_snap3_dm2]
        self.check_get_response(response, rqs_to_find)

    def test_rest_get_list_from_rqs_from_request(self):
        # As a user, I can get the list of RQS from the rqs they are bound to
        self.user1_req1_branch2_snap2_dm1 = DatedMeasure(
            owner=self.user1,
            request=self.user1_req1,
            request_query_snapshot=self.user1_req1_branch2_snap2,
            measure=10,
            fhir_datetime=datetime.now(tz=timezone.utc) + timedelta(days=-2)
        )
        self.user1_req1_branch2_snap2_dm1.save()
        url = reverse(
            'explorations:request-request-query-snapshot-dated-measures-list',
            kwargs=dict(parent_lookup_request_query_snapshot=self.user1_req1_branch2_snap3.uuid,
                        parent_lookup_request=self.user1_req1.uuid)
        )
        self.client.force_login(self.user1)
        response = self.client.get(url)
        response.render()
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        rqs_to_find = [self.user1_req1_branch2_snap3_dm1, self.user1_req1_branch2_snap3_dm2]
        self.check_get_response(response, rqs_to_find)

    def test_rest_get_list_from_request(self):
        # As a user, I can get the list of dated_measure from the Request they are bound to
        url = reverse(
            'explorations:request-dated-measures-list',
            kwargs=dict(parent_lookup_request=self.user1_req1.uuid)
        )
        self.client.force_login(self.user1)
        response = self.client.get(url)
        response.render()

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        rqs_to_find = [self.user1_req1_branch2_snap3_dm1, self.user1_req1_branch2_snap3_dm2]
        self.check_get_response(response, rqs_to_find)


class DatedMeasuresCreateTests(DatedMeasuresTests):
    @mock.patch('explorations.tasks.get_count_task.delay')
    def test_create_dm(self, count_task_delay):
        # As a user, I can create a dated_measure for one request_query_snapshot
        # Some fields are read only
        measure_test = 55
        datetime_test = datetime.now()

        read_only_fields = dict(
            count_task_id="test_task_id",
            request_job_id="test_job_id",
            request_job_status=FAILED_REQUEST_STATUS,
            request_job_fail_msg="test_fail_msg",
            request_job_duration=1001,
        )

        request = self.factory.post(DATED_MEASURES_URL, dict(
            request_query_snapshot_id=self.user1_req1_branch2_snap2.uuid,
            measure=measure_test,
            fhir_datetime=datetime_test,
            **read_only_fields
        ), format='json')
        force_authenticate(request, self.user1)
        response = self.create_view(request)
        response.render()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.content)
        count_task_delay.assert_not_called()

        dm = DatedMeasure.objects.filter(
            measure=measure_test,
            owner=self.user1,
            request_query_snapshot=self.user1_req1_branch2_snap2,
            fhir_datetime=datetime_test,
        ).first()
        self.assertIsNotNone(dm)

        for read_only_field, val in read_only_fields.items():
            self.assertNotEqual(getattr(dm, read_only_field, None), val, f"With field {read_only_field}: {val}")

    @mock.patch('explorations.tasks.get_count_task.delay')
    def test_rest_create_dm_from_rqs(self, count_task_delay):
        # As a user, I can create a dated_measure for one request_query_snapshot, from rsq' url
        measure_test = 55
        datetime_test = datetime.now()
        url = reverse(
            'explorations:request-query-snapshot-dated-measures-list',
            kwargs=dict(parent_lookup_request_query_snapshot=self.user1_req1_branch2_snap2.uuid)
        )
        self.client.force_login(self.user1)
        response = self.client.post(url, data=dict(
            measure=measure_test,
            fhir_datetime=datetime_test,
        ), format='json')
        response.render()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.content)
        count_task_delay.assert_not_called()

        rqs = DatedMeasure.objects.filter(
            measure=measure_test,
            owner=self.user1,
            request_query_snapshot=self.user1_req1_branch2_snap2,
            fhir_datetime=datetime_test,
        ).first()
        self.assertIsNotNone(rqs)

    @mock.patch('explorations.tasks.get_count_task.delay')
    def test_create_dm_via_fhir(self, count_task_delay):
        # As a user, I can create a dm without specifying a measure, it will ask FHIR back-end for the answer
        test_task_id = "test_id"

        request = self.factory.post(DATED_MEASURES_URL, dict(
            request_query_snapshot_id=self.user1_req1_branch2_snap2.uuid
        ), format='json')

        mocked_task_async_result = AsyncResult(id=test_task_id)
        count_task_delay.return_value = mocked_task_async_result

        force_authenticate(request, self.user1)
        response = self.create_view(request)
        response.render()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.content)
        count_task_delay.assert_called_once()

        self.assertIsNotNone(
            DatedMeasure.objects.filter(
                owner=self.user1,
                request_query_snapshot=self.user1_req1_branch2_snap2,
                count_task_id=test_task_id,
                request_job_status=PENDING_REQUEST_STATUS
            ).first()
        )

    @mock.patch('explorations.tasks.get_count_task.delay')
    def test_error_create_dm_with_forbidden_access(self, count_task_delay):
        forbidden_test_measure = 55
        forbidden_time = datetime.now().replace(tzinfo=timezone.utc)

        # As a user, I cannot create a dm without specifying a fhir_datetime, if I specify a measure
        request = self.factory.post(DATED_MEASURES_URL, dict(
            request_query_snapshot_id=self.user1_req1_branch2_snap2.uuid,
            measure=forbidden_test_measure,
        ), format='json')
        force_authenticate(request, self.user1)
        response = self.create_view(request)
        response.render()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.content)

        # As a user, I cannot create a cohort result while specifying
        forbidden_fields = dict(
            owner_id=[self.user2.uuid],                     # a wrong owner
            request_id=[self.user1_req2.uuid],              # a wrong request
        )

        for field, vals in forbidden_fields.items():
            for val in vals:
                data = dict(
                    request_query_snapshot_id=self.user1_req1_branch2_snap2.uuid,
                    measure=forbidden_test_measure,
                    fhir_datetime=forbidden_time,
                )
                data[field] = val

                request = self.factory.post(COHORTS_URL, data, format='json')
                force_authenticate(request, self.user1)
                response = self.create_view(request)
                response.render()
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST,
                                 f"With field {field}: {val}. Content: {response.content}")

        self.assertIsNone(DatedMeasure.objects.filter(
            measure=forbidden_test_measure
        ).first())
        self.assertIsNone(DatedMeasure.objects.filter(
            fhir_datetime=forbidden_time
        ).first())
        count_task_delay.assert_not_called()

    @mock.patch('explorations.tasks.get_count_task.delay')
    def test_error_create_dm_on_rqs_not_owned(self, count_task_delay):
        # As a user, I cannot create a dm on a Rqs I don't own
        forbidden_test_measure = 55

        request = self.factory.post(DATED_MEASURES_URL, dict(
            request_query_snapshot_id=self.user2_req1_snap1_dm1.uuid,
            measure=forbidden_test_measure,
            fhir_datetime=datetime.now()
        ), format='json')
        force_authenticate(request, self.user1)
        response = self.create_view(request)
        response.render()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.content)

        # even if created using fhir API
        request = self.factory.post(DATED_MEASURES_URL, dict(
            request_query_snapshot_id=self.user2_req1_snap1_dm1.uuid,
        ), format='json')
        force_authenticate(request, self.user1)
        response = self.create_view(request)
        response.render()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.content)

        self.assertIsNone(DatedMeasure.objects.filter(
            measure=forbidden_test_measure
        ).first())


class DatedMeasuresDeleteTests(DatedMeasuresTests):
    def setUp(self):
        super(DatedMeasuresDeleteTests, self).setUp()
        self.user1_req1_branch2_snap3_cohort1 = CohortResult(
            request_query_snapshot=self.user1_req1_branch2_snap3,
            request=self.user1_req1,
            owner=self.user1,
            dated_measure=self.user1_req1_branch2_snap3_dm1,
        )
        self.user1_req1_branch2_snap3_cohort1.save()

    def test_delete_owned_dm_without_cohort(self):
        # As a user, I can delete a dated measure I owned, not bound to a CohortResult
        request = self.factory.delete(DATED_MEASURES_URL)
        force_authenticate(request, self.user1)
        response = self.delete_view(request, uuid=self.user1_req1_branch2_snap3_dm2.uuid)
        response.render()

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT, response.content)
        self.assertIsNone(DatedMeasure.objects.filter(uuid=self.user1_req1_branch2_snap3.uuid).first())

    def test_error_delete_owned_dm_with_cohort(self):
        # As a user, I cannot delete a dated measure bound to a CohortResult
        request = self.factory.delete(DATED_MEASURES_URL)
        force_authenticate(request, self.user1)
        response = self.delete_view(request, uuid=self.user1_req1_branch2_snap3_dm1.uuid)
        response.render()

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.content)
        self.assertIsNotNone(DatedMeasure.objects.filter(uuid=self.user1_req1_branch2_snap3_dm1.uuid).first())

    def test_error_delete_not_owned(self):
        # As a user, I cannot delete a dated measure linekd to a CohortResult
        request = self.factory.delete(DATED_MEASURES_URL)
        force_authenticate(request, self.user2)
        response = self.delete_view(request, uuid=self.user1_req1_branch2_snap3_dm2.uuid)
        response.render()

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND, response.content)
        self.assertIsNotNone(DatedMeasure.objects.filter(uuid=self.user1_req1_branch2_snap3_dm2.uuid).first())


class DatedMeasuresUpdateTests(DatedMeasuresTests):
    def test_update_dm_as_owner(self):
        # As a user, I can update a dated measure I own
        new_measure = 55
        new_datetime = datetime.now().replace(tzinfo=timezone.utc)

        # Some fields are read only
        read_only_fields = dict(
            create_task_id="test_task_id",
            request_job_id="test_job_id",
            request_job_status=FINISHED_REQUEST_STATUS,
            request_job_fail_msg="test_fail_msg",
            request_job_duration=1001,
        )

        request = self.factory.patch(DATED_MEASURES_URL, dict(
            measure=new_measure,
            fhir_datetime=new_datetime,
            **read_only_fields
        ), format='json')
        force_authenticate(request, self.user1)
        response = self.update_view(request, uuid=self.user1_req1_branch2_snap3_dm1.uuid)
        response.render()

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        dm = DatedMeasure.objects.get(uuid=self.user1_req1_branch2_snap3_dm1.uuid)
        self.assertEqual(dm.measure, new_measure)
        self.assertEqual(dm.fhir_datetime, new_datetime)

        for read_only_field, val in read_only_fields.items():
            self.assertNotEqual(getattr(dm, read_only_field, None), val, f"With field {read_only_field}: {val}")

    def test_error_update_dm_as_not_owner(self):
        # As a user, I cannot update a dated_measure I don't own
        request = self.factory.patch(DATED_MEASURES_URL, dict(
            measure=55,
            fhir_datetime=datetime.now(),
        ), format='json')
        force_authenticate(request, self.user2)
        response = self.update_view(request, uuid=self.user1_req1_branch2_snap3_dm1.uuid)
        response.render()

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND, response.content)
        dm = DatedMeasure.objects.get(uuid=self.user1_req1_branch2_snap3_dm1.uuid)
        self.assertEqual(dm.measure, self.user1_req1_branch2_snap3_dm1.measure)
        self.assertEqual(dm.fhir_datetime, self.user1_req1_branch2_snap3_dm1.fhir_datetime.replace(tzinfo=timezone.utc))

    def test_error_update_dm_forbidden_fields(self):
        # As a user, I cannot update owner in a dated_measure I own
        request = self.factory.patch(DATED_MEASURES_URL, dict(
            owner_id=self.user2.uuid,
        ), format='json')
        force_authenticate(request, self.user1)
        response = self.update_view(request, uuid=self.user1_req1_branch2_snap3_dm1.uuid)
        response.render()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.content)

        # As a user, I cannot update request in a dated_measure I own
        request = self.factory.patch(DATED_MEASURES_URL, dict(
            request_id=self.user1_req2.uuid,
        ), format='json')
        force_authenticate(request, self.user1)
        response = self.update_view(request, uuid=self.user1_req1_branch2_snap3_dm1.uuid)
        response.render()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.content)

        # As a user, I cannot update rqs in a dated_measure I own
        request = self.factory.patch(DATED_MEASURES_URL, dict(
            request_query_snapshot_id=self.user1_req1_branch2_snap2.uuid,
        ), format='json')
        force_authenticate(request, self.user1)
        response = self.update_view(request, uuid=self.user1_req1_branch2_snap3_dm1.uuid)
        response.render()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.content)

        dm = DatedMeasure.objects.get(uuid=self.user1_req1_branch2_snap3_dm1.uuid)
        self.assertEqual(dm.owner_id, self.user1_req1_branch2_snap3_dm1.owner_id)
        self.assertEqual(dm.request_id, self.user1_req1_branch2_snap3_dm1.request_id)
        self.assertEqual(dm.request_query_snapshot_id, self.user1_req1_branch2_snap3_dm1.request_query_snapshot_id)


# COHORTS
class CohortsTests(RqsTests):
    def setUp(self):
        super(CohortsTests, self).setUp()
        self.user1_req1_branch2_snap3_dm1 = DatedMeasure(
            owner=self.user1,
            request=self.user1_req1,
            request_query_snapshot=self.user1_req1_branch2_snap3,
            measure=10,
            fhir_datetime=datetime.now(tz=timezone.utc) + timedelta(days=-2)
        )
        self.user1_req1_branch2_snap3_dm1.save()
        self.user1_req1_branch2_snap3_dm2 = DatedMeasure(
            owner=self.user1,
            request=self.user1_req1,
            request_query_snapshot=self.user1_req1_branch2_snap3,
            measure=20,
            fhir_datetime=datetime.now(tz=timezone.utc) + timedelta(days=-1)
        )
        self.user1_req1_branch2_snap3_dm2.save()

        self.user1_req1_branch2_snap3_cr1 = CohortResult(
            owner=self.user1,
            request=self.user1_req1,
            request_query_snapshot=self.user1_req1_branch2_snap3,
            fhir_group_id="group11231",
            dated_measure=self.user1_req1_branch2_snap3_dm1
        )
        self.user1_req1_branch2_snap3_cr1.save()

        self.user1_req1_branch2_snap2_dm1 = DatedMeasure(
            owner=self.user1,
            request=self.user1_req1,
            request_query_snapshot=self.user1_req1_branch2_snap3,
            measure=10,
            fhir_datetime=datetime.now(tz=timezone.utc) + timedelta(days=-2)
        )
        self.user1_req1_branch2_snap2_dm1.save()

        self.user1_req1_branch2_snap2_cr1 = CohortResult(
            owner=self.user1,
            request=self.user1_req1,
            request_query_snapshot=self.user1_req1_branch2_snap2,
            fhir_group_id="group11221",
            dated_measure=self.user1_req1_branch2_snap3_dm1
        )
        self.user1_req1_branch2_snap2_cr1.save()

        self.user2_req1_snap1_dm1 = DatedMeasure(
            owner=self.user2,
            request=self.user2_req1,
            request_query_snapshot=self.user2_req1_snap1,
            measure=20,
            fhir_datetime=datetime.now(tz=timezone.utc) + timedelta(days=-1)
        )
        self.user2_req1_snap1_dm1.save()

        self.user2_req1_snap1_cr1 = CohortResult(
            owner=self.user2,
            request=self.user2_req1,
            request_query_snapshot=self.user2_req1_snap1,
            fhir_group_id="group2111",
            dated_measure=self.user2_req1_snap1_dm1
        )
        self.user2_req1_snap1_cr1.save()

        self.list_view = RequestViewSet.as_view({'get': 'list'})
        self.retrieve_view = CohortResultViewSet.as_view({'get': 'retrieve'})
        self.create_view = CohortResultViewSet.as_view({'post': 'create'})
        self.delete_view = CohortResultViewSet.as_view({'delete': 'destroy'})
        self.update_view = CohortResultViewSet.as_view({'patch': 'partial_update'})


class CohortsGetTests(CohortsTests):
    def test_user_simple_get(self):
        # As a user, I can get a request I did
        request = self.factory.get(f'{COHORTS_URL}')
        force_authenticate(request, self.user1)
        response = self.retrieve_view(request, uuid=self.user1_req1_branch2_snap2_cr1.uuid)
        response.render()
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        cr_to_find = self.user1_req1_branch2_snap2_cr1
        self.check_get_response(response, cr_to_find)

    def test_error_wrong_user(self):
        # As a user, I can't get a request user 2 created
        request = self.factory.get(f'{COHORTS_URL}')
        force_authenticate(request, self.user1)
        response = self.retrieve_view(request, uuid=self.user2_req1_snap1_cr1.uuid)
        response.render()
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND, response.content)

    def test_rest_get_list_from_rqs(self):
        # As a user, I can get the list of cohorts from the rqs they are bound to
        self.user1_req1_branch2_snap3_cr2 = CohortResult(
            owner=self.user1,
            request=self.user1_req1,
            request_query_snapshot=self.user1_req1_branch2_snap3,
            fhir_group_id="group25",
            dated_measure=self.user1_req1_branch2_snap3_dm2
        )
        self.user1_req1_branch2_snap3_cr2.save()
        url = reverse(
            'explorations:request-query-snapshot-cohort-results-list',
            kwargs=dict(parent_lookup_request_query_snapshot=self.user1_req1_branch2_snap3.uuid)
        )
        self.client.force_login(self.user1)
        response = self.client.get(url)
        response.render()

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        rqs_to_find = [self.user1_req1_branch2_snap3_cr1, self.user1_req1_branch2_snap3_cr2]
        self.check_get_response(response, rqs_to_find)

    def test_rest_get_list_from_rqs_from_request(self):
        # As a user, I can get the list of cohorts from the rqs they are bound to
        self.user1_req1_branch2_snap3_cr2 = CohortResult(
            owner=self.user1,
            request=self.user1_req1,
            request_query_snapshot=self.user1_req1_branch2_snap3,
            fhir_group_id="group25",
            dated_measure=self.user1_req1_branch2_snap3_dm2
        )
        self.user1_req1_branch2_snap3_cr2.save()
        url = reverse(
            'explorations:request-request-query-snapshot-cohort-results-list',
            kwargs=dict(parent_lookup_request_query_snapshot=self.user1_req1_branch2_snap3.uuid,
                        parent_lookup_request=self.user1_req1.uuid)
        )
        self.client.force_login(self.user1)
        response = self.client.get(url)
        response.render()

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        rqs_to_find = [self.user1_req1_branch2_snap3_cr1, self.user1_req1_branch2_snap3_cr2]
        self.check_get_response(response, rqs_to_find)

    def test_rest_get_list_from_request(self):
        # As a user, I can get the list of cohorts from the Request they are bound to
        self.user1_req1_branch2_snap3_cr2 = CohortResult(
            owner=self.user1,
            request=self.user1_req1,
            request_query_snapshot=self.user1_req1_branch2_snap3,
            fhir_group_id="group11232",
            dated_measure=self.user1_req1_branch2_snap3_dm2
        )
        self.user1_req1_branch2_snap3_cr2.save()
        self.user1_req2_branch2_snap2_cr1 = CohortResult(
            owner=self.user1,
            request=self.user1_req2,
            request_query_snapshot=self.user1_req1_branch2_snap2,
            fhir_group_id="group12221",
            dated_measure=self.user1_req1_branch2_snap2_dm1
        )
        self.user1_req1_branch2_snap2_cr1.save()

        url = reverse(
            'explorations:request-cohort-results-list',
            kwargs=dict(parent_lookup_request=self.user1_req1.uuid)
        )
        self.client.force_login(self.user1)
        response = self.client.get(url)
        response.render()

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        rqs_to_find = [self.user1_req1_branch2_snap3_cr1, self.user1_req1_branch2_snap3_cr2,
                       self.user1_req1_branch2_snap2_cr1]
        self.check_get_response(response, rqs_to_find)


class CohortsCreateTests(CohortsTests):
    @mock.patch('explorations.tasks.create_cohort_task.delay')
    def test_create(self, create_task_delay):
        # As a user, I can create a CohortResult
        # Some fields are read only
        # Some fields are optional
        test_name = "My new cohort"
        test_description = "Cohort I just did"
        test_measure = 55
        test_datetime = datetime.now().replace(tzinfo=timezone.utc)
        test_fhir_group_id = "group_id"

        read_only_fields = dict(
            create_task_id="test_task_id",
            request_job_id="test_job_id",
            request_job_status=FINISHED_REQUEST_STATUS,
            request_job_fail_msg="test_fail_msg",
            request_job_duration=1001,
        )

        optional_fields = ["name", "description"]

        cohort = self.factory.post(COHORTS_URL, dict(
            name=test_name,
            description=test_description,
            request_query_snapshot_id=self.user1_req1_branch2_snap3.uuid,
            dated_measure=dict(
                measure=test_measure,
                fhir_datetime=test_datetime,
            ),
            fhir_group_id=test_fhir_group_id,
            **read_only_fields
        ), format='json')
        force_authenticate(cohort, self.user1)
        response = self.create_view(cohort)
        response.render()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.content)
        create_task_delay.assert_not_called()

        cr = CohortResult.objects.filter(
            name=test_name,
            description=test_description,
            request_query_snapshot=self.user1_req1_branch2_snap3.uuid,
            fhir_group_id=test_fhir_group_id
        ).first()
        self.assertIsNotNone(cr)

        dm = DatedMeasure.objects.filter(
            measure=test_measure,
            fhir_datetime=test_datetime,
        ).first()
        self.assertIsNotNone(dm)

        for read_only_field, val in read_only_fields.items():
            self.assertNotEqual(getattr(dm, read_only_field, None), val, f"With field {read_only_field}: {val}")

    @mock.patch('explorations.tasks.create_cohort_task.delay')
    def test_create_minimal(self, create_task_delay):
        # As a user, I can create a CohortResult with the minimum of fields
        test_measure = 654
        test_datetime = datetime.now().replace(tzinfo=timezone.utc)
        test_fhir_group_id = "group_id"

        cohort = self.factory.post(COHORTS_URL, dict(
            request_query_snapshot_id=self.user1_req1_branch2_snap3.uuid,
            dated_measure=dict(
                measure=test_measure,
                fhir_datetime=test_datetime,
            ),
            fhir_group_id=test_fhir_group_id,
        ), format='json')
        force_authenticate(cohort, self.user1)
        response = self.create_view(cohort)
        response.render()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.content)
        create_task_delay.assert_not_called()

        cr = CohortResult.objects.filter(
            request_query_snapshot=self.user1_req1_branch2_snap3.uuid,
            fhir_group_id=test_fhir_group_id
        ).first()
        self.assertIsNotNone(cr)

        dm = DatedMeasure.objects.filter(
            measure=test_measure,
            fhir_datetime=test_datetime,
        ).first()
        self.assertIsNotNone(dm)

    @mock.patch('explorations.tasks.create_cohort_task.delay')
    def test_create_with_fhir(self, create_task_delay):
        # As a user, I can create a CohortResult without providing group_id
        # Fhir API will then be called in create_task
        test_name = "My new cohort"
        test_description = "Cohort I just did"
        test_task_id = "test_id"

        mocked_task_async_result = AsyncResult(id=test_task_id)
        create_task_delay.return_value = mocked_task_async_result

        cohort = self.factory.post(COHORTS_URL, dict(
            name=test_name,
            description=test_description,
            request_query_snapshot_id=self.user1_req1_branch2_snap3.uuid,
        ), format='json')
        force_authenticate(cohort, self.user1)
        response = self.create_view(cohort)
        response.render()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.content)
        create_task_delay.assert_called_once()

        cr = CohortResult.objects.filter(
            name=test_name,
            description=test_description,
            request_query_snapshot=self.user1_req1_branch2_snap3.uuid,
            create_task_id=test_task_id,
            request_job_status=PENDING_REQUEST_STATUS
        ).first()
        self.assertIsNotNone(cr)
        self.assertIsNone(cr.dated_measure.fhir_datetime)
        self.assertIsNone(cr.dated_measure.measure)

    @mock.patch('explorations.tasks.create_cohort_task.delay')
    def test_create_with_dm_id(self, create_task_delay):
        # As a user, I can create a CohortResult while providing a dated_measure
        # the cohort result will be bound to it
        test_name = "My new cohort"
        test_description = "Cohort I just did"
        test_fhir_group_id = "group_id"

        cohort = self.factory.post(COHORTS_URL, dict(
            name=test_name,
            description=test_description,
            request_query_snapshot_id=self.user1_req1_branch2_snap3.uuid,
            dated_measure_id=self.user1_req1_branch2_snap3_dm1.uuid,
            fhir_group_id=test_fhir_group_id
        ), format='json')
        force_authenticate(cohort, self.user1)
        response = self.create_view(cohort)
        response.render()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.content)
        create_task_delay.assert_not_called()

        cr = CohortResult.objects.filter(
            name=test_name,
            description=test_description,
            request_query_snapshot=self.user1_req1_branch2_snap3.uuid,
            dated_measure=self.user1_req1_branch2_snap3_dm1.uuid,
            fhir_group_id=test_fhir_group_id
        ).first()
        self.assertIsNotNone(cr)

    @mock.patch('explorations.tasks.create_cohort_task.delay')
    def test_create_with_dm_id_with_fhir(self, create_task_delay):
        # As a user, I can create a CohortResult while providing a dated_measure
        # the cohort result will be bound to it
        # If no group_id is provided, cohort_result and dated_measure will be updated with FHIR API

        test_name = "My new cohort"
        test_description = "Cohort I just did"
        test_task_id = "test_id"

        mocked_task_async_result = AsyncResult(id=test_task_id)
        create_task_delay.return_value = mocked_task_async_result

        cohort = self.factory.post(COHORTS_URL, dict(
            name=test_name,
            description=test_description,
            request_query_snapshot_id=self.user1_req1_branch2_snap3.uuid,
            dated_measure_id=self.user1_req1_branch2_snap3_dm1.uuid
        ), format='json')
        force_authenticate(cohort, self.user1)
        response = self.create_view(cohort)
        response.render()

        create_task_delay.assert_called_once()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.content)
        cr = CohortResult.objects.filter(
            name=test_name,
            description=test_description,
            request_query_snapshot=self.user1_req1_branch2_snap3.uuid,
            dated_measure=self.user1_req1_branch2_snap3_dm1.uuid,
            create_task_id=test_task_id
        ).first()
        self.assertIsNotNone(cr)

    def test_rest_create_from_rqs(self):
        # As a user, I can create a CohortResult, from the bound rqs' url
        test_name = "My new cohort"
        test_description = "Cohort I just did"
        test_measure = 5985
        test_datetime = datetime.now().replace(tzinfo=timezone.utc)
        # Client() will use DjangoJsonEncoder for datetimes that will truncate microseconds
        test_datetime = test_datetime.replace(microsecond=1000 * (round(test_datetime.microsecond / 1000)))
        test_fhir_group_id = "group_id"

        url = reverse(
            'explorations:request-query-snapshot-cohort-results-list',
            kwargs=dict(parent_lookup_request_query_snapshot=self.user1_req1_branch2_snap3.uuid)
        )

        self.client.force_login(self.user1)
        response = self.client.post(url, data=dict(
            name=test_name,
            description=test_description,
            dated_measure=dict(
                measure=test_measure,
                fhir_datetime=test_datetime,
            ),
            fhir_group_id=test_fhir_group_id
        ), content_type='application/json')
        response.render()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.content)
        cr = CohortResult.objects.filter(
            name=test_name,
            description=test_description,
            request_query_snapshot=self.user1_req1_branch2_snap3.uuid,
            fhir_group_id=test_fhir_group_id
        ).first()
        self.assertIsNotNone(cr)

        dm = DatedMeasure.objects.filter(
            measure=test_measure,
            fhir_datetime=test_datetime,
        ).first()
        self.assertIsNotNone(dm)

    def test_rest_create_with_dm_id_from_rqs(self):
        # As a user, I can create a CohortResult
        test_name = "My new cohort"
        test_description = "Cohort I just did"

        url = reverse(
            'explorations:request-query-snapshot-cohort-results-list',
            kwargs=dict(parent_lookup_request_query_snapshot=self.user1_req1_branch2_snap3.uuid)
        )

        self.client.force_login(self.user1)
        response = self.client.post(url, data=dict(
            name=test_name,
            description=test_description,
            dated_measure_id=self.user1_req1_branch2_snap3_dm1.uuid
        ), format='json')
        response.render()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.content)
        cr = CohortResult.objects.filter(
            name=test_name,
            description=test_description,
            request_query_snapshot=self.user1_req1_branch2_snap3.uuid,
            dated_measure=self.user1_req1_branch2_snap3_dm1.uuid
        ).first()
        self.assertIsNotNone(cr)

    def test_error_create_with_forbidden_fields(self):
        test_name = "My new forbidden cohort"
        test_description = "Cohort I just did"
        test_measure = 55
        test_datetime = datetime.now().replace(tzinfo=timezone.utc)
        test_fhir_group_id = "group_id"

        # As a user, I cannot create a cohort result while specifying
        forbidden_fields = dict(
            owner_id=[self.user2.uuid],                     # a wrong owner
            request_id=[self.user1_req2.uuid],              # a wrong request
            type=["MY_PATIENTS"]                           # a custom type
        )

        for field, vals in forbidden_fields.items():
            for val in vals:
                data = dict(
                    name=test_name,
                    description=test_description,
                    request_query_snapshot_id=self.user1_req1_branch2_snap3.uuid,
                    dated_measure=dict(
                        measure=test_measure,
                        fhir_datetime=test_datetime,
                    ),
                    fhir_group_id=test_fhir_group_id,
                )
                data[field] = val

            request = self.factory.post(COHORTS_URL, data, format='json')
            force_authenticate(request, self.user1)
            response = self.create_view(request)
            response.render()
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST,
                             f"With field {field}: {val}. Content: {response.content}")

        self.assertIsNone(CohortResult.objects.filter(name=test_name).first())

    def test_error_create_with_wrong_owner(self):
        # As a user, I cannot create a cohort result on a rqs I don't own
        test_name = "My new cohort"
        test_description = "Cohort I just did"
        test_measure = 55
        test_datetime = datetime.now().replace(tzinfo=timezone.utc)
        test_fhir_group_id = "group_id"

        request = self.factory.post(COHORTS_URL, dict(
            name=test_name,
            description=test_description,
            request_query_snapshot_id=self.user1_req1_branch2_snap3.uuid,
            dated_measure=dict(
                measure=test_measure,
                fhir_datetime=test_datetime,
            ),
            fhir_group_id=test_fhir_group_id
        ), format='json')
        force_authenticate(request, self.user2)
        response = self.create_view(request)
        response.render()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.content)
        self.assertIsNone(CohortResult.objects.filter(
            name=test_name).first())

        # Even if I create through Fhir API
        request = self.factory.post(COHORTS_URL, dict(
            name=test_name,
            description=test_description,
            request_query_snapshot_id=self.user1_req1_branch2_snap3.uuid,
            dated_measure=dict(
                measure=test_measure,
                fhir_datetime=test_datetime,
            )
        ), format='json')
        force_authenticate(request, self.user2)
        response = self.create_view(request)
        response.render()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.content)
        self.assertIsNone(CohortResult.objects.filter(
            name=test_name).first())


class CohortsDeleteTests(CohortsTests):
    def test_delete_as_owner(self):
        # As a user, I can delete a cohort result I created
        request = self.factory.delete(COHORTS_URL)
        force_authenticate(request, self.user1)
        response = self.delete_view(request, uuid=self.user1_req1_branch2_snap2_cr1.uuid)
        response.render()

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT, response.content)
        self.assertIsNone(CohortResult.objects.filter(
            uuid=self.user1_req1_branch2_snap2_cr1.uuid
        ).first())

    def test_error_delete_as_not_owner(self):
        # As a user, I cannot delete another user's cohort result
        request = self.factory.delete(COHORTS_URL)
        force_authenticate(request, self.user2)
        response = self.delete_view(request, uuid=self.user1_req1_branch2_snap2_cr1.uuid)
        response.render()

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND, response.content)
        self.assertIsNotNone(CohortResult.objects.filter(
            uuid=self.user1_req1_branch2_snap2_cr1.uuid
        ).first())


class CohortsUpdateTests(CohortsTests):
    def test_update_cohort_as_owner(self):
        # As a user, I can update a cohort result I created
        test_id = "other_id"
        test_name = "New name"
        test_description = "New description"

        # Some fields are read only
        read_only_fields = dict(
            create_task_id="test_task_id",
            request_job_id="test_job_id",
            request_job_status=FINISHED_REQUEST_STATUS,
            request_job_fail_msg="test_fail_msg",
            request_job_duration=1001,
        )

        request = self.factory.patch(COHORTS_URL, dict(
            fhir_group_id=test_id,
            name=test_name,
            description=test_description,
            **read_only_fields
        ), format='json')
        force_authenticate(request, self.user1)
        response = self.update_view(request, uuid=self.user1_req1_branch2_snap2_cr1.uuid)
        response.render()

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        cr = CohortResult.objects.get(uuid=self.user1_req1_branch2_snap2_cr1.uuid)
        self.assertEqual(cr.fhir_group_id, test_id)
        self.assertEqual(cr.name, test_name)
        self.assertEqual(cr.description, test_description)

        for read_only_field, val in read_only_fields.items():
            self.assertNotEqual(getattr(cr, read_only_field, None), val, f"With field {read_only_field}: {val}")

    def test_error_update_cohort_as_not_owner(self):
        # As a user, I cannot update another user's cohort result
        test_id = "other_id"
        request = self.factory.patch(COHORTS_URL, dict(
            fhir_group_id=test_id,
        ), format='json')
        force_authenticate(request, self.user2)
        response = self.update_view(request, uuid=self.user1_req1_branch2_snap2_cr1.uuid)
        response.render()

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND, response.content)
        cr = CohortResult.objects.get(uuid=self.user1_req1_branch2_snap2_cr1.uuid)
        self.assertNotEqual(cr.fhir_group_id, test_id)

    def test_error_update_cohort_forbidden_fields(self):
        # As a user, I cannot update owner in a cohort result I created
        request = self.factory.patch(COHORTS_URL, dict(
            owner_id=self.user2.uuid,
        ), format='json')
        force_authenticate(request, self.user1)
        response = self.update_view(request, uuid=self.user1_req1_branch2_snap2_cr1.uuid)
        response.render()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.content)

        # As a user, I cannot update request in a cohort result I created
        request = self.factory.patch(COHORTS_URL, dict(
            request_id=self.user1_req2.uuid,
        ), format='json')
        force_authenticate(request, self.user1)
        response = self.update_view(request, uuid=self.user1_req1_branch2_snap2_cr1.uuid)
        response.render()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.content)

        # As a user, I cannot update request_query_snapshot in a cohort result I created
        request = self.factory.patch(COHORTS_URL, dict(
            request_query_snapshot_id=self.user1_req1_branch2_snap3.uuid,
        ), format='json')
        force_authenticate(request, self.user1)
        response = self.update_view(request, uuid=self.user1_req1_branch2_snap2_cr1.uuid)
        response.render()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.content)

        # As a user, I cannot update dated_measure in a cohort result I created
        request = self.factory.patch(COHORTS_URL, dict(
            dated_measure_id=self.user1_req1_branch2_snap3_dm1.uuid,
        ), format='json')
        force_authenticate(request, self.user1)
        response = self.update_view(request, uuid=self.user1_req1_branch2_snap2_cr1.uuid)
        response.render()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.content)

        # As a user, I cannot update type in a cohort result I created
        request = self.factory.patch(COHORTS_URL, dict(
            type="MY_PATIENTS",
        ), format='json')
        force_authenticate(request, self.user1)
        response = self.update_view(request, uuid=self.user1_req1_branch2_snap2_cr1.uuid)
        response.render()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.content)

        cr = CohortResult.objects.get(uuid=self.user1_req1_branch2_snap2_cr1.uuid)
        self.assertEqual(cr.owner_id, self.user1_req1_branch2_snap2_cr1.owner_id)
        self.assertEqual(cr.request_id, self.user1_req1_branch2_snap2_cr1.request_id)
        self.assertEqual(cr.request_query_snapshot_id, self.user1_req1_branch2_snap2_cr1.request_query_snapshot_id)
        self.assertEqual(cr.dated_measure_id, self.user1_req1_branch2_snap2_cr1.dated_measure_id)
        self.assertEqual(cr.type, self.user1_req1_branch2_snap2_cr1.type)


# TASKS
class TasksTests(RqsTests):
    def setUp(self):
        super(TasksTests, self).setUp()
        self.user1_req1_snap1_empty_dm = DatedMeasure(
            owner=self.user1,
            request=self.user1_req1,
            request_query_snapshot=self.user1_req1_snap1,
            count_task_id="task_id",
            request_job_status=PENDING_REQUEST_STATUS
        )
        self.user1_req1_snap1_empty_dm.save()

        self.user1_req1_snap1_empty_cohort = CohortResult(
            owner=self.user1,
            request=self.user1_req1,
            request_query_snapshot=self.user1_req1_snap1,
            name="My empty cohort",
            description="so empty",
            create_task_id="task_id",
            request_job_status=PENDING_REQUEST_STATUS,
            dated_measure=self.user1_req1_snap1_empty_dm
        )
        self.user1_req1_snap1_empty_cohort.save()

    @mock.patch('explorations.tasks.fhir_api')
    def test_get_count_task(self, mock_fhir_api):
        test_count = 102
        test_datetime = datetime.now().replace(tzinfo=timezone.utc)
        test_job_id = "job_id"
        test_job_duration = 1000

        mock_fhir_api.post_count_cohort.return_value = FhirCountResponse(
            count=test_count,
            fhir_datetime=test_datetime,
            fhir_job_id="job_id",
            job_duration=test_job_duration,
            success=True,
        )
        get_count_task({}, '{"json_key": "json_value"}', self.user1_req1_snap1_empty_dm.uuid)

        new_dm = DatedMeasure.objects.filter(
            uuid=self.user1_req1_snap1_empty_dm.uuid,
            measure=test_count,
            fhir_datetime=test_datetime,
            request_job_duration=test_job_duration,
            request_job_status=FINISHED_REQUEST_STATUS,
            request_job_id=test_job_id,
            count_task_id=self.user1_req1_snap1_empty_dm.count_task_id
        ).first()
        # TODO: I could not find how to test that intermediate state of request_job_status is set to 'started'
        #  while calling Fhir API
        self.assertIsNotNone(new_dm)

    @mock.patch('explorations.tasks.fhir_api')
    def test_failed_get_count_task(self, mock_fhir_api):
        test_job_duration = 1000
        test_err_msg = "Error"
        test_fhir_job_id = "job_id"

        mock_fhir_api.post_count_cohort.return_value = FhirCountResponse(
            fhir_job_id=test_fhir_job_id,
            job_duration=test_job_duration,
            success=False,
            err_msg=test_err_msg,
        )

        get_count_task({}, '{"json_key": "json_value"}', self.user1_req1_snap1_empty_dm.uuid)

        new_dm = DatedMeasure.objects.filter(
            uuid=self.user1_req1_snap1_empty_dm.uuid,
            request_job_id=test_fhir_job_id,
            request_job_duration=test_job_duration,
            request_job_status=FAILED_REQUEST_STATUS,
            request_job_fail_msg=test_err_msg,
            count_task_id=self.user1_req1_snap1_empty_dm.count_task_id
        ).first()
        # TODO: I could not find how to test that intermediate state of request_job_status is set to 'started'
        # while calling Fhir API
        self.assertIsNotNone(new_dm)
        self.assertIsNone(new_dm.measure)
        self.assertIsNone(new_dm.fhir_datetime)

    @mock.patch('explorations.tasks.fhir_api')
    def test_create_cohort_task(self, mock_fhir_api):
        test_count = 102
        test_datetime = datetime.now().replace(tzinfo=timezone.utc)
        test_job_id = "job_id"
        test_job_duration = 1000
        test_group_id = "groupId"

        mock_fhir_api.post_create_cohort.return_value = FhirCohortResponse(
            count=test_count,
            group_id=test_group_id,
            fhir_datetime=test_datetime,
            fhir_job_id="job_id",
            job_duration=test_job_duration,
            success=True,
        )
        create_cohort_task({}, '{"json_key": "json_value"}', self.user1_req1_snap1_empty_cohort.uuid)

        new_cr = CohortResult.objects.filter(
            uuid=self.user1_req1_snap1_empty_cohort.uuid,
            request_job_duration=test_job_duration,
            request_job_status=FINISHED_REQUEST_STATUS,
            request_job_id=test_job_id,
            fhir_group_id=test_group_id,
            create_task_id=self.user1_req1_snap1_empty_cohort.create_task_id
        ).first()
        # TODO: I could not find how to test that intermediate state of request_job_status is set to 'started'
        #  while calling Fhir API
        self.assertIsNotNone(new_cr)
        self.assertEqual(new_cr.dated_measure.measure, test_count)
        self.assertEqual(new_cr.dated_measure.count_task_id, new_cr.create_task_id)
        self.assertEqual(new_cr.dated_measure.request_job_id, new_cr.request_job_id)
        self.assertEqual(new_cr.dated_measure.request_job_status, new_cr.request_job_status)
        self.assertEqual(new_cr.dated_measure.request_job_fail_msg, new_cr.request_job_fail_msg)
        self.assertEqual(new_cr.dated_measure.request_job_duration, new_cr.request_job_duration)

    @mock.patch('explorations.tasks.fhir_api')
    def test_failed_create_cohort_task(self, mock_fhir_api):
        test_job_duration = 1000
        test_err_msg = "Error"
        test_fhir_job_id = "job_id"

        mock_fhir_api.post_create_cohort.return_value = FhirCohortResponse(
            fhir_job_id=test_fhir_job_id,
            job_duration=test_job_duration,
            success=False,
            err_msg=test_err_msg,
        )

        create_cohort_task({}, '{"json_key": "json_value"}', self.user1_req1_snap1_empty_cohort.uuid)

        new_cr = CohortResult.objects.filter(
            uuid=self.user1_req1_snap1_empty_cohort.uuid,
            request_job_id=test_fhir_job_id,
            request_job_duration=test_job_duration,
            request_job_status=FAILED_REQUEST_STATUS,
            request_job_fail_msg=test_err_msg,
            create_task_id=self.user1_req1_snap1_empty_cohort.create_task_id
        ).first()
        # TODO: I could not find how to test that intermediate state of request_job_status is set to 'started'
        # while calling Fhir API
        self.assertIsNotNone(new_cr)
        self.assertIsNone(new_cr.dated_measure.measure)
        self.assertIsNone(new_cr.dated_measure.fhir_datetime)
        self.assertEqual(new_cr.fhir_group_id, "")
        self.assertEqual(new_cr.dated_measure.request_job_id, new_cr.request_job_id)
        self.assertEqual(new_cr.dated_measure.request_job_status, new_cr.request_job_status)
        self.assertEqual(new_cr.dated_measure.request_job_fail_msg, new_cr.request_job_fail_msg)
        self.assertEqual(new_cr.dated_measure.request_job_duration, new_cr.request_job_duration)
