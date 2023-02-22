import random
from datetime import timedelta
from typing import List
from unittest import mock
from unittest.mock import MagicMock

from django.utils import timezone
from rest_framework import status
from rest_framework.test import force_authenticate

from admin_cohort.tests_tools import random_str, ListCase, RetrieveCase, CaseRetrieveFilter, CreateCase, DeleteCase, \
    PatchCase
from admin_cohort.tools import prettify_json
from admin_cohort.types import JobStatus
from cohort.models import DatedMeasure, RequestQuerySnapshot, CohortResult
from cohort.models.dated_measure import DATED_MEASURE_MODE_CHOICES
from cohort.tests.tests_view_rqs import RqsTests
from cohort.views import DatedMeasureViewSet, NestedDatedMeasureViewSet


class DatedMeasuresTests(RqsTests):
    unupdatable_fields = ["owner", "request_query_snapshot", "uuid",
                          "mode", "count_task_id", "fhir_datetime",
                          "measure", "measure_min", "measure_max",
                          "created_at", "modified_at", "deleted"]
    unsettable_default_fields = dict(
        request_job_status=JobStatus.started)
    unsettable_fields = ["owner", "uuid", "count_task_id",
                         "created_at", "modified_at", "deleted", ]
    manual_dupplicated_fields = []

    objects_url = "cohort/dated-measures/"
    retrieve_view = DatedMeasureViewSet.as_view({'get': 'retrieve'})
    list_view = DatedMeasureViewSet.as_view({'get': 'list'})
    create_view = DatedMeasureViewSet.as_view({'post': 'create'})
    delete_view = DatedMeasureViewSet.as_view({'delete': 'destroy'})
    update_view = DatedMeasureViewSet.as_view(
        {'patch': 'partial_update'})
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
            is_active_branch=True,
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
    def __init__(self, mock_task_called: bool, **kwargs):
        super(DMCreateCase, self).__init__(**kwargs)
        self.mock_task_called = mock_task_called


class DatedMeasuresCreateTests(DatedMeasuresTests):
    @mock.patch('cohort.serializers.cohort_job_api.get_authorization_header')
    @mock.patch('cohort.tasks.get_count_task.delay')
    def check_create_case_with_mock(self, case: DMCreateCase, mock_task: MagicMock, mock_header: MagicMock,
                                    other_view: any, view_kwargs: dict):
        mock_header.return_value = None
        mock_task.return_value = None

        super(DatedMeasuresCreateTests, self).check_create_case(case, other_view, **(view_kwargs or {}))

        mock_task.assert_called() if case.mock_task_called else mock_task.assert_not_called()
        mock_header.assert_called() if case.mock_task_called else mock_header.assert_not_called()

    def check_create_case(self, case: DMCreateCase, other_view: any = None,
                          **view_kwargs):
        return self.check_create_case_with_mock(
            case, other_view=other_view or None, view_kwargs=view_kwargs)

    def setUp(self):
        super(DatedMeasuresCreateTests, self).setUp()

        self.basic_data = dict(
            request_query_snapshot=self.user1_req1_snap1.pk,
            mode=DATED_MEASURE_MODE_CHOICES[0][0],
        )
        self.basic_case = DMCreateCase(
            data=self.basic_data,
            status=status.HTTP_201_CREATED,
            user=self.user1,
            success=True,
            mock_task_called=True,
            retrieve_filter=DMCaseRetrieveFilter(
                request_query_snapshot__pk=self.user1_req1_snap1.pk)
        )
        self.basic_err_case = self.basic_case.clone(
            mock_task_called=False,
            success=False,
            status=status.HTTP_400_BAD_REQUEST,
        )

    def test_create(self):
        # As a user, I can create a DatedMeasure with only RQS,
        # it will launch a task
        self.check_create_case(self.basic_case)

    def test_create_with_data(self):
        # As a user, I can create a DatedMeasure with all fields,
        # no task will be launched
        self.check_create_case(self.basic_case.clone(
            data={
                **self.basic_data,
                'measure': 1,
                'measure_min': 1,
                'measure_max': 1,
                'fhir_datetime': timezone.now(),
            },
            mock_task_called=False,
        ))

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

    def test_error_create_missing_time_or_measure(self):
        # As a user, I cannot create a dm if I provide one of fhir_datetime
        # and measure but not both
        cases = (self.basic_err_case.clone(
            data={**self.basic_data, k: v},
        ) for (k, v) in {'fhir_datetime': timezone.now(), 'measure': 1}.items())
        [self.check_create_case(case) for case in cases]

    def test_error_create_missing_field(self):
        # As a user, I cannot create a dm if some field is missing
        cases = (self.basic_err_case.clone(
            data={**self.basic_data, k: None},
        ) for k in ['request_query_snapshot'])
        [self.check_create_case(case) for case in cases]

    def test_error_create_with_other_owner(self):
        # As a user, I cannot create a DM providing another user as owner
        self.check_create_case(self.basic_err_case.clone(
            data={**self.basic_data, 'owner': self.user2.pk},
        ))

    def test_create_from_rqs(self):
        # As a user, I can create a RQS specifying a previous snapshot
        # using nestedViewSet
        self.check_create_case(self.basic_case.clone(
            data={},
        ), NestedDatedMeasureViewSet.as_view({'post': 'create'}),
            request_query_snapshot=self.user1_req1_snap1.pk)

    def test_error_create_on_rqs_not_owned(self):
        # As a user, I cannot create a dm on a Rqs I don't own
        self.check_create_case(self.basic_err_case.clone(
            data={**self.basic_data,
                  'request_query_snapshot': self.user2_req1_snap1.pk},
        ))


class DMDeleteCase(DeleteCase):
    def __init__(self, with_cohort: bool = False, **kwargs):
        super(DMDeleteCase, self).__init__(**kwargs)
        self.with_cohort = with_cohort


class DatedMeasuresDeleteTests(DatedMeasuresTests):
    def check_delete_case(self, case: DMDeleteCase):
        obj = self.model_objects.create(**case.data_to_delete)

        if case.with_cohort:
            CohortResult.objects.create(
                dated_measure=obj,
                request_query_snapshot=obj.request_query_snapshot,
                owner=obj.owner,
            )

        request = self.factory.delete(self.objects_url)
        force_authenticate(request, case.user)
        response = self.__class__.delete_view(
            request, **{self.model._meta.pk.name: obj.pk}
        )
        response.render()

        self.assertEqual(
            response.status_code, case.status,
            msg=(f"{case.description}"
                 + (f" -> {prettify_json(response.content)}"
                    if response.content else "")),
        )

        obj = self.model.all_objects.filter(pk=obj.pk).first()

        if case.success:
            self.check_is_deleted(obj)
        else:
            self.assertIsNotNone(obj)
            self.assertIsNone(obj.deleted)
            obj.delete()

    def setUp(self):
        super(DatedMeasuresDeleteTests, self).setUp()
        self.basic_data = dict(
            owner=self.user1,
            request_query_snapshot=self.user1_req1_snap1,
            fhir_datetime=timezone.now(),
            measure=1,
            measure_min=1,
            measure_max=1,
            count_task_id="test",
            mode=DATED_MEASURE_MODE_CHOICES[0][0],
            created_at=timezone.now(),
            modified_at=timezone.now(),
            request_job_id="test",
            request_job_status=JobStatus.pending.value,
            request_job_fail_msg="test",
            request_job_duration="1s",
        )
        self.basic_case = DMDeleteCase(
            data_to_delete=self.basic_data,
            status=status.HTTP_204_NO_CONTENT,
            success=True,
            user=self.user1,
        )
        self.basic_err_case = self.basic_case.clone(
            status=status.HTTP_403_FORBIDDEN,
            success=False,
            user=self.user1,
        )

    def test_delete_owned_dm_without_cohort(self):
        # As a user, I can delete a dated measure I owned,
        # not bound to a CohortResult
        self.check_delete_case(self.basic_case)

    def test_error_delete_owned_dm_with_cohort(self):
        # As a user, I cannot delete a dated measure bound to a CohortResult
        self.check_delete_case(self.basic_err_case.clone(
            with_cohort=True
        ))

    def test_error_delete_not_owned(self):
        # As a user, I cannot delete a dated measure linekd to a CohortResult
        self.check_delete_case(self.basic_err_case.clone(
            user=self.user2,
            status=status.HTTP_404_NOT_FOUND,
        ))


class DatedMeasuresUpdateTests(DatedMeasuresTests):
    def setUp(self):
        super(DatedMeasuresUpdateTests, self).setUp()
        self.basic_data = dict(
            owner=self.user1,
            request_query_snapshot=self.user1_req1_snap1,
            fhir_datetime=timezone.now(),
            measure=1,
            measure_min=1,
            measure_max=1,
            count_task_id="test",
            mode=DATED_MEASURE_MODE_CHOICES[0][0],
            created_at=timezone.now(),
            modified_at=timezone.now(),
            request_job_id="test",
            request_job_status=JobStatus.pending.value,
            request_job_fail_msg="test",
            request_job_duration="1s",
        )
        self.basic_err_case = PatchCase(
            data_to_update=dict(measure=10),
            initial_data=self.basic_data,
            status=status.HTTP_403_FORBIDDEN,
            success=False,
            user=self.user1,
        )

    def test_error_update(self):
        # As a user, I cannot update a DatedMeasure I own
        self.check_patch_case(self.basic_err_case)

    def test_error_update_dm_as_not_owner(self):
        # As a user, I cannot update a dated_measure I don't own
        self.check_patch_case(self.basic_err_case.clone(
            status=status.HTTP_403_FORBIDDEN,
            initial_data={**self.basic_data, 'owner': self.user2}
        ))
