import random
from datetime import timedelta
from typing import List, Any
from unittest import mock
from unittest.mock import MagicMock

from django.utils import timezone
from rest_framework import status

from admin_cohort.tests.tests_tools import random_str, ListCase, RetrieveCase, CaseRetrieveFilter, CreateCase, DeleteCase, PatchCase
from admin_cohort.types import JobStatus
from cohort.models import DatedMeasure, RequestQuerySnapshot, Request
from cohort.models.dated_measure import DATED_MEASURE_MODE_CHOICES, GLOBAL_DM_MODE
from cohort.tests.tests_view_rqs import RqsTests
from cohort.views import DatedMeasureViewSet


class DatedMeasuresTests(RqsTests):
    unupdatable_fields = ["owner", "request_query_snapshot", "uuid",
                          "mode", "count_task_id", "fhir_datetime",
                          "created_at", "modified_at", "deleted"]
    unsettable_default_fields = {}
    unsettable_fields = ["owner", "uuid", "count_task_id",
                         "created_at", "modified_at", "deleted"]
    manual_dupplicated_fields = []

    objects_url = "cohort/dated-measures/"
    retrieve_view = DatedMeasureViewSet.as_view({'get': 'retrieve'})
    list_view = DatedMeasureViewSet.as_view({'get': 'list'})
    create_view = DatedMeasureViewSet.as_view({'post': 'create'})
    delete_view = DatedMeasureViewSet.as_view({'delete': 'destroy'})
    update_view = DatedMeasureViewSet.as_view({'patch': 'partial_update'})
    model = DatedMeasure
    model_objects = DatedMeasure.objects
    model_fields = DatedMeasure._meta.fields

    def setUp(self):
        super(DatedMeasuresTests, self).setUp()

        self.user1_req1_snap1 = RequestQuerySnapshot.objects.create(
            owner=self.user1,
            request=self.user1_req1,
            serialized_query='{}',
        )
        self.user1_req1_branch1_snap2 = RequestQuerySnapshot.objects.create(
            owner=self.user1,
            request=self.user1_req1,
            previous_snapshot=self.user1_req1_snap1,
            serialized_query='{"perimeter": "Terra"}',
        )
        self.user2_req1_snap1 = RequestQuerySnapshot.objects.create(
            owner=self.user2,
            request=self.user2_req1,
            serialized_query='{}',
        )


class DatedMeasuresGetTests(DatedMeasuresTests):
    def setUp(self):
        super(DatedMeasuresGetTests, self).setUp()
        self.rqss: List[RequestQuerySnapshot] = sum((list(
            u.user_request_query_snapshots.all()) for u in self.users), [])

        to_create: List[DatedMeasure] = []
        for i in range(200):
            rqs = random.choice(self.rqss)
            to_create.append(DatedMeasure(
                request_query_snapshot=rqs,
                owner=rqs.owner,
                measure=random.randint(0, 20),
                mode=random.choice(DATED_MEASURE_MODE_CHOICES)[0],
                count_task_id=random_str(15),
            ))

        self.dms: List[DatedMeasure] = DatedMeasure.objects.bulk_create(
            to_create)

    def test_list(self):
        # As a user, I can list the DM I own
        case = ListCase(
            to_find=[dm for dm in self.dms if dm.owner == self.user1],
            user=self.user1,
            success=True,
            status=status.HTTP_200_OK
        )
        self.check_get_paged_list_case(case)

    def test_retrieve(self):
        # As a user, I can retrieve a single DM I own
        to_find = [dm for dm in self.dms if dm.owner == self.user1][0]
        case = RetrieveCase(
            to_find=to_find,
            view_params=dict(uuid=to_find.pk),
            user=self.user1,
            success=True,
            status=status.HTTP_200_OK
        )
        self.check_retrieve_case(case)

    def test_error_get_not_owned(self):
        # As a user, I cannot retrieve a single DM I do not own
        to_find = [dm for dm in self.dms if dm.owner == self.user2][0]
        case = RetrieveCase(
            to_find=to_find,
            view_params=dict(uuid=to_find.pk),
            user=self.user1,
            success=False,
            status=status.HTTP_404_NOT_FOUND
        )
        self.check_retrieve_case(case)


class DMCaseRetrieveFilter(CaseRetrieveFilter):
    def __init__(self, request_query_snapshot__pk: str = "", **kwargs):
        self.request_query_snapshot__pk = request_query_snapshot__pk
        super(DMCaseRetrieveFilter, self).__init__(**kwargs)


class DMCreateCase(CreateCase):
    def __init__(self, mock_header_called: bool, mock_count_task_called: bool, mock_cancel_task_called: bool, **kwargs):
        super(DMCreateCase, self).__init__(**kwargs)
        self.mock_header_called = mock_header_called
        self.mock_count_task_called = mock_count_task_called
        self.mock_cancel_task_called = mock_cancel_task_called


class DatedMeasuresCreateTests(DatedMeasuresTests):

    def setUp(self):
        super(DatedMeasuresCreateTests, self).setUp()

        self.basic_data = dict(
            request_query_snapshot_id=self.user1_req1_snap1.pk,
            mode=DATED_MEASURE_MODE_CHOICES[0][0],
        )
        self.basic_case = DMCreateCase(
            data=self.basic_data,
            status=status.HTTP_201_CREATED,
            user=self.user1,
            success=True,
            mock_header_called=True,
            mock_count_task_called=True,
            mock_cancel_task_called=True,
            retrieve_filter=DMCaseRetrieveFilter(request_query_snapshot__pk=self.user1_req1_snap1.pk)
        )
        self.basic_err_case = self.basic_case.clone(
            mock_count_task_called=False,
            success=False,
            status=status.HTTP_400_BAD_REQUEST,
        )
        self.req_with_running_dms = Request.objects.create(
            owner=self.user1,
            name="Request with running DMs",
            description="Request with DMs started, pending",
            parent_folder=self.user1_folder1
        )
        self.user1_req_running_dms_snap1 = RequestQuerySnapshot.objects.create(
            owner=self.user1,
            request=self.req_with_running_dms,
            serialized_query='{}',
        )
        self.started_dm = DatedMeasure.objects.create(request_query_snapshot=self.user1_req_running_dms_snap1,
                                                      request_job_status=JobStatus.started,
                                                      owner=self.user1)
        self.pending_dm = DatedMeasure.objects.create(request_query_snapshot=self.user1_req_running_dms_snap1,
                                                      request_job_status=JobStatus.pending,
                                                      owner=self.user1)

    @mock.patch('cohort.services.dated_measure.cancel_previous_count_jobs.apply_async')
    @mock.patch('cohort.services.dated_measure.count_cohort.apply_async')
    def check_create_case_with_mock(self, case: DMCreateCase, mock_count_task: MagicMock, mock_cancel_task: MagicMock,
                                    other_view: any, view_kwargs: dict):
        mock_cancel_task.return_value = None
        mock_count_task.return_value = None

        with self.captureOnCommitCallbacks(execute=True):
            super(DatedMeasuresCreateTests, self).check_create_case(case, other_view, **(view_kwargs or {}))

        mock_cancel_task.assert_called() if case.mock_cancel_task_called else mock_cancel_task.assert_not_called()
        mock_count_task.assert_called() if case.mock_count_task_called else mock_count_task.assert_not_called()

    def check_create_case(self, case: DMCreateCase, other_view: Any = None, **view_kwargs):
        return self.check_create_case_with_mock(case, other_view=other_view or None, view_kwargs=view_kwargs)

    def test_create(self):
        # As a user, I can create a DatedMeasure with only RQS,
        # it will launch a task
        self.check_create_case(self.basic_case)

    def test_create_with_unread_fields(self):
        # As a user, I can create a dm
        self.check_create_case(self.basic_case.clone(
            data={**self.basic_data,
                  'request_job_fail_msg': "test",
                  'request_job_id': "test",
                  'count_task_id': "test",
                  'request_job_duration': '1',
                  'created_at': timezone.now() + timedelta(hours=1),
                  'modified_at': timezone.now() + timedelta(hours=1),
                  'deleted': timezone.now() + timedelta(hours=1)},
        ))

    def test_error_create_missing_field(self):
        # As a user, I cannot create a dm if some field is missing
        case = self.basic_err_case.clone(data={**self.basic_data,
                                               "request_query_snapshot_id": None},
                                         mock_header_called=False,
                                         mock_cancel_task_called=False)
        self.check_create_case(case)

    def test_error_create_with_other_owner(self):
        # As a user, I cannot create a DM providing another user as owner
        self.check_create_case(self.basic_err_case.clone(data={**self.basic_data, 'owner': self.user2.pk},
                                                         mock_header_called=False,
                                                         mock_cancel_task_called=False))

    def test_error_create_on_rqs_not_provided(self):
        # cannot create a DM without an RQS
        case = self.basic_err_case.clone(data={'request_query_snapshot_id': None},
                                         mock_header_called=False,
                                         mock_cancel_task_called=False)
        self.check_create_case(case=case)

    def test_error_create_on_rqs_not_owned(self):
        # As a user, I cannot create a DM on a RQS I don't own
        case = self.basic_err_case.clone(data={'request_query_snapshot_id': self.user2_req1_snap1.pk},
                                         mock_header_called=False,
                                         mock_cancel_task_called=False)
        self.check_create_case(case=case)

    def test_create_with_request_having_running_dms(self):
        # before create new DM, cancel any previously running ones
        case = self.basic_case.clone(data={'request_query_snapshot_id': self.user1_req_running_dms_snap1.pk},
                                     retrieve_filter=DMCaseRetrieveFilter(request_query_snapshot__pk=self.user1_req_running_dms_snap1.pk))
        self.check_create_case(case)


class DMDeleteCase(DeleteCase):
    def __init__(self, with_cohort: bool = False, **kwargs):
        super(DMDeleteCase, self).__init__(**kwargs)
        self.with_cohort = with_cohort


class DMUpdateTests(DatedMeasuresTests):
    def setUp(self):
        super(DMUpdateTests, self).setUp()
        self.basic_data = dict(request_query_snapshot_id=self.user1_req1_snap1.pk,
                               mode=DATED_MEASURE_MODE_CHOICES[0][0],
                               owner=self.user1)
        self.basic_case = PatchCase(initial_data=self.basic_data,
                                    status=status.HTTP_200_OK,
                                    success=True,
                                    user=self.user1,
                                    data_to_update={})
        self.basic_err_case = self.basic_case.clone(status=status.HTTP_400_BAD_REQUEST,
                                                    success=False)

    @mock.patch('admin_cohort.services.ws_event_manager.WebsocketManager.send_to_client')
    @mock.patch('cohort_job_server.cohort_counter.CohortCounter.handle_patch_dated_measure')
    def check_dm_patch_case(self, mock_patch_handler, mock_ws_send_to_client, case: dict):
        mock_patch_handler.return_value = None
        mock_ws_send_to_client.return_value = None
        resp_data = self.check_patch_case(case=case["patch_case"],
                                          return_response_data=True)
        self.assertEqual(resp_data.get("request_job_status"), JobStatus.finished.value)
        mock_patch_handler.assert_called_once() if case["mock_patch_handler_called"] else mock_patch_handler.assert_not_called()
        mock_ws_send_to_client.assert_called_once() if case["mock_ws_send_to_client_called"] else mock_ws_send_to_client.assert_not_called()

    def test_patch_dm_with_status_finished(self):
        normal_dm_case = {"patch_case": self.basic_case.clone(data_to_update={'request_job_status': 'finished'}),
                          "mock_patch_handler_called": True,
                          "mock_ws_send_to_client_called": True
                          }
        self.check_dm_patch_case(case=normal_dm_case)

    def test_patch_global_dm_with_status_finished(self):
        global_dm_case = {"patch_case": self.basic_case.clone(initial_data={**self.basic_data, "mode": GLOBAL_DM_MODE},
                                                              data_to_update={'request_job_status': 'finished'}),
                          "mock_patch_handler_called": True,
                          "mock_ws_send_to_client_called": False
                          }
        self.check_dm_patch_case(case=global_dm_case)

    @mock.patch('admin_cohort.services.ws_event_manager.WebsocketManager.send_to_client')
    @mock.patch('cohort_job_server.cohort_counter.CohortCounter.handle_patch_dated_measure')
    def test_error_patch_dm_with_invalid_status(self, mock_patch_handler, mock_ws_send_to_client):
        mock_patch_handler.side_effect = ValueError('Wrong status value')
        mock_ws_send_to_client.return_value = None
        case = self.basic_err_case.clone(data_to_update={'request_job_status': 'invalid_status'})
        self.check_patch_case(case)
        mock_patch_handler.assert_called_once()
        mock_ws_send_to_client.assert_called_once()
