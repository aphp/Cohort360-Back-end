import random
from datetime import timedelta
from typing import List, Any
from unittest import mock
from unittest.mock import MagicMock

from django.utils import timezone
from rest_framework import status
from rest_framework.test import force_authenticate

from admin_cohort.tools.tests_tools import random_str, ListCase, RetrieveCase, CaseRetrieveFilter, CreateCase, DeleteCase, PatchCase
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

    @mock.patch('cohort.services.dated_measure.get_authorization_header')
    @mock.patch('cohort.services.dated_measure.cancel_previously_running_dm_jobs.delay')
    @mock.patch('cohort.services.dated_measure.get_count_task.delay')
    def check_create_case_with_mock(self, case: DMCreateCase, mock_count_task: MagicMock, mock_cancel_task: MagicMock, mock_header: MagicMock,
                                    other_view: any, view_kwargs: dict):
        mock_header.return_value = None
        mock_cancel_task.return_value = None
        mock_count_task.return_value = None

        with self.captureOnCommitCallbacks(execute=True):
            super(DatedMeasuresCreateTests, self).check_create_case(case, other_view, **(view_kwargs or {}))

        mock_header.assert_called() if case.mock_header_called else mock_header.assert_not_called()
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

    # def test_error_create_on_cancel_running_dms(self):
    #     case = self.basic_err_case.clone(data={'request_query_snapshot_id': self.user1_req_running_dms_snap1.pk},
    #                                      status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    #                                      cancel_task_raises_exception=True)
    #     self.check_create_case(case)


class DMDeleteCase(DeleteCase):
    def __init__(self, with_cohort: bool = False, **kwargs):
        super(DMDeleteCase, self).__init__(**kwargs)
        self.with_cohort = with_cohort


class DMUpdateTests(DatedMeasuresTests):
    def setUp(self):
        super(DMUpdateTests, self).setUp()
        self.user1_req1_snap1_dm: DatedMeasure = DatedMeasure.objects.create(
                                                                        owner=self.user1,
                                                                        request_query_snapshot=self.user1_req1_snap1,
                                                                        measure=1,
                                                                        fhir_datetime=timezone.now())
        self.basic_data = dict(request_query_snapshot_id=self.user1_req1_snap1.pk,
                               mode=DATED_MEASURE_MODE_CHOICES[0][0],
                               owner=self.user1)
        self.data_global_estimate_mode = self.basic_data.copy()
        self.data_global_estimate_mode.update({"mode": GLOBAL_DM_MODE})

        self.basic_case = PatchCase(initial_data=self.basic_data,
                                    status=status.HTTP_200_OK,
                                    success=True,
                                    user=self.user1,
                                    data_to_update={})

        self.basic_err_case = self.basic_case.clone(status=status.HTTP_400_BAD_REQUEST,
                                                    success=False)

    def test_update_dm_by_sjs_callback_status_finished(self):
        dm: DatedMeasure = self.model_objects.create(**self.basic_data)
        data = {'request_job_status': 'finished',
                'count': 10500
                }
        request = self.factory.patch(self.objects_url, data=data, format='json')
        force_authenticate(request, dm.owner)
        response = self.__class__.update_view(request, **{self.model._meta.pk.name: dm.uuid})
        response.render()
        self.assertEqual(response.data.get("request_job_status"), JobStatus.finished.value)
        self.assertEqual(response.data.get("measure"), data['count'])

    def test_update_dm_with_global_estimate_by_sjs_callback_status_finished(self):
        dm_global: DatedMeasure = self.model_objects.create(**self.data_global_estimate_mode)
        data = {'request_job_status': 'finished',
                'minimum': 10,
                'maximum': 50}
        request = self.factory.patch(self.objects_url, data=data, format='json')
        force_authenticate(request, dm_global.owner)
        response = self.__class__.update_view(request, **{self.model._meta.pk.name: dm_global.uuid})
        response.render()
        self.assertEqual(response.data.get("request_job_status"), JobStatus.finished.value)
        self.assertEqual(response.data.get("measure_min"), data['minimum'])
        self.assertEqual(response.data.get("measure_max"), data['maximum'])

    def test_update_dm_by_sjs_callback_status_failed(self):
        dm: DatedMeasure = self.model_objects.create(**self.basic_data)
        data = {'request_job_status': 'error',
                'message': 'Error on count job'
                }
        request = self.factory.patch(self.objects_url, data=data, format='json')
        force_authenticate(request, dm.owner)
        response = self.__class__.update_view(request, **{self.model._meta.pk.name: dm.uuid})
        response.render()
        self.assertEqual(response.data.get("request_job_status"), JobStatus.failed.value)
        self.assertIsNotNone(response.data.get("request_job_fail_msg"))
        self.assertIsNotNone(response.data.get("request_job_duration"))

    def test_error_update_dm_by_sjs_callback_invalid_status(self):
        invalid_status = 'invalid_status'
        case = self.basic_err_case.clone(data_to_update={'request_job_status': invalid_status})
        self.check_patch_case(case)
