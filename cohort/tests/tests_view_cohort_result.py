import random
from datetime import timedelta
from smtplib import SMTPException
from typing import List
from unittest import mock
from unittest.mock import MagicMock

from django.utils import timezone
from rest_framework import status
from rest_framework.test import force_authenticate

from admin_cohort.tools.tests_tools import random_str, ListCase, RetrieveCase, CaseRetrieveFilter, CreateCase, PatchCase
from admin_cohort.types import JobStatus
from cohort.models import CohortResult, RequestQuerySnapshot, DatedMeasure
from cohort.models.dated_measure import GLOBAL_DM_MODE, SNAPSHOT_DM_MODE
from cohort.tests.tests_view_dated_measure import DatedMeasuresTests, DMDeleteCase
from cohort.views import CohortResultViewSet


class CohortsTests(DatedMeasuresTests):
    unupdatable_fields = ["owner", "request_query_snapshot", "uuid",
                          "type", "create_task_id", "dated_measure",
                          "request_job_id",
                          "created_at", "modified_at", "deleted"]
    unsettable_default_fields = dict(request_job_status=JobStatus.new)
    unsettable_fields = ["owner", "uuid", "create_task_id",
                         "created_at", "modified_at", "deleted", ]
    manual_dupplicated_fields = []

    objects_url = "cohort/cohorts/"
    retrieve_view = CohortResultViewSet.as_view({'get': 'retrieve'})
    list_view = CohortResultViewSet.as_view({'get': 'list'})
    create_view = CohortResultViewSet.as_view({'post': 'create'})
    delete_view = CohortResultViewSet.as_view({'delete': 'destroy'})
    update_view = CohortResultViewSet.as_view({'patch': 'partial_update'})
    get_active_jobs_view = CohortResultViewSet.as_view({'get': 'get_active_jobs'})
    model = CohortResult
    model_objects = CohortResult.objects
    model_fields = CohortResult._meta.fields

    def setUp(self):
        super(CohortsTests, self).setUp()


class CohortsGetTests(CohortsTests):
    def setUp(self):
        super(CohortsGetTests, self).setUp()
        self.rqss: List[RequestQuerySnapshot] = sum((list(
            u.user_request_query_snapshots.all()) for u in self.users), [])
        self.str_pattern = "aAa"

        to_create: List[DatedMeasure] = []
        crs_to_create: List[CohortResult] = []
        for i in range(200):
            rqs = random.choice(self.rqss)
            dm = DatedMeasure(
                request_query_snapshot=rqs,
                owner=rqs.owner,
                measure=random.randint(0, 20),
                mode=SNAPSHOT_DM_MODE,
                count_task_id=random_str(15),
                fhir_datetime=(timezone.now()
                               - timedelta(days=random.randint(1, 5))),
            )
            to_create.append(dm)

            dm_global = None
            if random.random() > .5:
                dm_global = DatedMeasure(
                    request_query_snapshot=rqs,
                    owner=rqs.owner,
                    measure=random.randint(0, 20),
                    mode=GLOBAL_DM_MODE,
                    count_task_id=random_str(15),
                )
                to_create.append(dm_global)

            crs_to_create.append(CohortResult(
                owner=dm.owner,
                name=random_str(10, random.random() > .5
                                and self.str_pattern),
                description=random_str(10, random.random() > .5
                                       and self.str_pattern),
                favorite=random.random() > .5,
                request_query_snapshot=dm.request_query_snapshot,
                fhir_group_id=random_str(10, with_space=False),
                request_job_status=random.choice(JobStatus.list()),
                dated_measure=dm,
                dated_measure_global=dm_global,
                create_task_id=random_str(10),
            ))

        self.dms: List[DatedMeasure] = DatedMeasure.objects.bulk_create(
            to_create)
        self.crs: List[CohortResult] = CohortResult.objects.bulk_create(
            crs_to_create)
        self.active_jobs_url = self.objects_url + 'jobs/active/'

    def test_list(self):
        # As a user, I can list the CR I own
        case = ListCase(
            to_find=[cr for cr in self.crs if cr.owner == self.user1],
            user=self.user1,
            success=True,
            status=status.HTTP_200_OK
        )
        self.check_get_paged_list_case(case)

    def test_retrieve(self):
        # As a user, I can retrieve a single CR I own
        to_find = [cr for cr in self.crs if cr.owner == self.user1][0]
        case = RetrieveCase(
            to_find=to_find,
            view_params=dict(uuid=to_find.pk),
            user=self.user1,
            success=True,
            status=status.HTTP_200_OK
        )
        self.check_retrieve_case(case)

    def test_error_get_not_owned(self):
        # As a user, I cannot retrieve a single CR I do not own
        to_find = [cr for cr in self.crs if cr.owner == self.user2][0]
        case = RetrieveCase(
            to_find=to_find,
            view_params=dict(uuid=to_find.pk),
            user=self.user1,
            success=False,
            status=status.HTTP_404_NOT_FOUND
        )
        self.check_retrieve_case(case)

    def test_list_with_filters(self):
        # As a user, I can list the CRs I own applying filters
        basic_case = ListCase(user=self.user1, success=True, status=status.HTTP_200_OK)
        crs = [cr for cr in self.crs if cr.owner == self.user1]
        rqs = self.user1.user_request_query_snapshots.first()
        req = rqs.request
        first_cr: CohortResult = self.user1.user_cohorts.first()
        example_measure = 10
        example_datetime = timezone.now() - timedelta(days=2)

        cases = [
            basic_case.clone(params=dict(request_job_status=JobStatus.pending.value),
                             to_find=[cr for cr in crs if cr.request_job_status == JobStatus.pending]),
            basic_case.clone(params=dict(name=self.str_pattern),
                             to_find=[cr for cr in crs if self.str_pattern.lower() in cr.name.lower()]),
            basic_case.clone(params=dict(min_result_size=example_measure),
                             to_find=[cr for cr in crs if cr.dated_measure.measure >= example_measure]),
            basic_case.clone(params=dict(max_result_size=example_measure),
                             to_find=[cr for cr in crs if cr.dated_measure.measure <= example_measure]),
            basic_case.clone(params=dict(min_fhir_datetime=example_datetime.isoformat()),
                             to_find=[cr for cr in crs if cr.dated_measure.fhir_datetime >= example_datetime]),
            basic_case.clone(params=dict(max_fhir_datetime=example_datetime.isoformat()),
                             to_find=[cr for cr in crs if cr.dated_measure.fhir_datetime <= example_datetime]),
            basic_case.clone(params=dict(favorite=True),
                             to_find=[cr for cr in crs if cr.favorite]),
            basic_case.clone(params=dict(fhir_group_id=first_cr.fhir_group_id),
                             to_find=[first_cr]),
            basic_case.clone(params=dict(request_query_snapshot=rqs.pk),
                             to_find=list(rqs.cohort_results.all())),
            basic_case.clone(params=dict(request_query_snapshot__request=req.pk),
                             to_find=sum((list(rqs.cohort_results.all()) for rqs in req.query_snapshots.all()), [])),
            basic_case.clone(params=dict(request_id=req.pk),
                             to_find=sum((list(rqs.cohort_results.all()) for rqs in req.query_snapshots.all()), []))
        ]
        [self.check_get_paged_list_case(case) for case in cases]

    def test_count_cohorts_with_active_jobs(self):
        request = self.factory.get(path=self.active_jobs_url)
        force_authenticate(request, self.user1)
        response = self.__class__.get_active_jobs_view(request)
        self.assertIn(response.status_code, (200, 204))
        if response.status_code == 200:
            self.assertGreater(response.data.get('jobs_count'), 0)

    def test_count_cohorts_with_no_active_jobs(self):
        for cohort in CohortResult.objects.all():
            cohort.request_job_status = JobStatus.finished
            cohort.save()
        request = self.factory.get(path=self.active_jobs_url)
        force_authenticate(request, self.user1)
        response = self.__class__.get_active_jobs_view(request)
        self.assertEqual(response.status_code, 204)


class CohortCaseRetrieveFilter(CaseRetrieveFilter):
    def __init__(self, name: str = "", **kwargs):
        self.name = name
        super(CohortCaseRetrieveFilter, self).__init__(**kwargs)


class CohortCreateCase(CreateCase):
    def __init__(self, mock_create_task_called: bool, **kwargs):
        super(CohortCreateCase, self).__init__(**kwargs)
        self.mock_create_task_called = mock_create_task_called


class CohortsCreateTests(CohortsTests):
    @mock.patch('cohort.serializers.cohort_job_api.get_authorization_header')
    @mock.patch('cohort.tasks.create_cohort_task.delay')
    @mock.patch('cohort.tasks.get_count_task.delay')
    def check_create_case_with_mock(self, case: CohortCreateCase, mock_count_task: MagicMock, mock_create_task: MagicMock,
                                    mock_header: MagicMock, other_view: any, view_kwargs: dict):
        mock_header.return_value = None
        mock_create_task.return_value = None
        mock_count_task.return_value = None

        with self.captureOnCommitCallbacks(execute=True):
            super(CohortsCreateTests, self).check_create_case(case, other_view, **(view_kwargs or {}))

        if case.success:
            inst = self.model_objects.filter(**case.retrieve_filter.args)\
                                     .exclude(**case.retrieve_filter.exclude).first()
            self.assertIsNotNone(inst.dated_measure)

            if case.data.get('global_estimate'):
                self.assertIsNotNone(inst.dated_measure_global)
                mock_create_task.assert_called() if case.mock_create_task_called else mock_create_task.assert_not_called()

        mock_create_task.assert_called() if case.mock_create_task_called else mock_create_task.assert_not_called()
        mock_header.assert_called() if case.mock_create_task_called else mock_header.assert_not_called()

    def check_create_case(self, case: CohortCreateCase, other_view: any = None, **view_kwargs):
        return self.check_create_case_with_mock(case, other_view=other_view or None, view_kwargs=view_kwargs)

    def setUp(self):
        super(CohortsCreateTests, self).setUp()

        self.test_name = "test"

        self.user1_req1_snap1_dm = DatedMeasure.objects.create(owner=self.user1,
                                                               request_query_snapshot=self.user1_req1_snap1,
                                                               measure=1,
                                                               fhir_datetime=timezone.now())

        self.basic_data = dict(
            name=self.test_name,
            description=self.test_name,
            favorite=True,
            request_query_snapshot=self.user1_req1_snap1.pk,
            dated_measure=self.user1_req1_snap1_dm.pk,
            # fhir_group_id
            # dated_measure_global
            # create_task_id
            # type
        )
        self.basic_case = CohortCreateCase(
            data=self.basic_data,
            status=status.HTTP_201_CREATED,
            user=self.user1,
            success=True,
            mock_create_task_called=True,
            retrieve_filter=CohortCaseRetrieveFilter(name=self.test_name),
            global_estimate=False
        )
        self.basic_err_case = self.basic_case.clone(
            mock_create_task_called=False,
            success=False,
            status=status.HTTP_400_BAD_REQUEST,
        )

    def test_create(self):
        # As a user, I can create a DatedMeasure with only RQS,
        # it will launch a task
        self.check_create_case(self.basic_case)

    def test_create_with_global(self):
        # As a user, I can create a DatedMeasure with only RQS,
        # it will launch a task
        self.check_create_case(self.basic_case.clone(
            data={**self.basic_data, 'global_estimate': True}
        ))

    def test_create_with_unread_fields(self):
        # As a user, I can create a dm
        self.check_create_case(self.basic_case.clone(
            data={**self.basic_data,
                  'create_task_id': random_str(5),
                  'request_job_fail_msg': random_str(5),
                  'request_job_id': random_str(5),
                  'request_job_duration': '1',
                  'created_at': timezone.now() + timedelta(hours=1),
                  'modified_at': timezone.now() + timedelta(hours=1),
                  'deleted': timezone.now() + timedelta(hours=1)},
        ))

    def test_error_create_missing_field(self):
        # As a user, I cannot create a dm if some field is missing
        cases = (self.basic_err_case.clone(
            data={**self.basic_data, k: None},
            success=False,
            status=status.HTTP_400_BAD_REQUEST,
        ) for k in ['request_query_snapshot'])
        [self.check_create_case(case) for case in cases]

    def test_error_create_with_other_owner(self):
        # As a user, I cannot create a cohort providing another user as owner
        self.check_create_case(self.basic_err_case.clone(
            data={**self.basic_data, 'owner': self.user2.pk},
            status=status.HTTP_400_BAD_REQUEST,
            success=False,
        ))

    def test_error_create_on_rqs_not_owned(self):
        # As a user, I cannot create a dm on a Rqs I don't own
        self.check_create_case(self.basic_err_case.clone(
            data={**self.basic_data,
                  'request_query_snapshot': self.user2_req1_snap1.pk},
            success=False,
            status=status.HTTP_400_BAD_REQUEST,
        ))


class CohortsDeleteTests(CohortsTests):

    def setUp(self):
        super(CohortsDeleteTests, self).setUp()
        self.user1_req1_snap1_dm: DatedMeasure = DatedMeasure.objects.create(
            owner=self.user1,
            request_query_snapshot=self.user1_req1_snap1,
            measure=1,
            fhir_datetime=timezone.now(),
        )
        self.basic_data = dict(
            owner=self.user1,
            request_query_snapshot=self.user1_req1_snap1,
            dated_measure=self.user1_req1_snap1_dm,
            create_task_id="test",
            created_at=timezone.now(),
            modified_at=timezone.now(),
            request_job_id="test",
            request_job_status=JobStatus.pending.value,
            request_job_fail_msg="test",
            request_job_duration="1s",
        )

    def test_delete_owned_dm_without_cohort(self):
        # As a user, I can delete a cohort result I owned
        self.check_delete_case(DMDeleteCase(
            data_to_delete=self.basic_data,
            status=status.HTTP_204_NO_CONTENT,
            success=True,
            user=self.user1,
        ))

    def test_error_delete_not_owned(self):
        # As a user, I cannot delete a cohort result linekd to a CohortResult
        self.check_delete_case(DMDeleteCase(
            data_to_delete=self.basic_data,
            status=status.HTTP_404_NOT_FOUND,
            success=False,
            user=self.user2,
        ))


class CohortsUpdateTests(CohortsTests):
    def setUp(self):
        super(CohortsUpdateTests, self).setUp()
        self.user1_req1_snap1_dm: DatedMeasure = DatedMeasure.objects.create(
                                                                        owner=self.user1,
                                                                        request_query_snapshot=self.user1_req1_snap1,
                                                                        measure=1,
                                                                        fhir_datetime=timezone.now())
        self.basic_data = dict(owner=self.user1,
                               request_query_snapshot=self.user1_req1_snap1,
                               dated_measure=self.user1_req1_snap1_dm,
                               create_task_id="test",
                               created_at=timezone.now(),
                               modified_at=timezone.now(),
                               request_job_id="test",
                               request_job_status=JobStatus.pending.value,
                               request_job_fail_msg="test",
                               request_job_duration="1s")

        self.basic_case = PatchCase(initial_data=self.basic_data,
                                    status=status.HTTP_200_OK,
                                    success=True,
                                    user=self.user1,
                                    data_to_update={})

        self.basic_err_case = self.basic_case.clone(status=status.HTTP_400_BAD_REQUEST,
                                                    success=False)

    def test_update_cohort_as_owner(self):
        # As a user, I can patch a CR I own
        data_to_update = dict(name="new_name",
                              description="new_desc",
                              request_job_status=JobStatus.finished,
                              request_job_fail_msg="test_fail_msg",
                              # read_only
                              create_task_id="test_task_id",
                              request_job_id="test_job_id",
                              created_at=timezone.now() + timedelta(hours=1),
                              modified_at=timezone.now() + timedelta(hours=1),
                              deleted=timezone.now() + timedelta(hours=1)
                              )
        self.check_patch_case(self.basic_case.clone(data_to_update=data_to_update))

    def test_error_update_cohort_as_not_owner(self):
        # As a user, I cannot update another user's cohort result
        case = self.basic_err_case.clone(data_to_update=dict(name="new_name"),
                                         user=self.user2,
                                         status=status.HTTP_404_NOT_FOUND)
        self.check_patch_case(case)

    def test_error_update_cohort_forbidden_fields(self):
        user1_req1_snap1_dm2: DatedMeasure = DatedMeasure.objects.create(owner=self.user1,
                                                                         request_query_snapshot=self.user1_req1_snap1,
                                                                         measure=2,
                                                                         fhir_datetime=timezone.now())
        cases = [self.basic_err_case.clone(data_to_update={k: v})
                 for k, v in dict(owner=self.user2.pk,
                                  request_query_snapshot=self.user1_req1_branch1_snap2.pk,
                                  dated_measure=user1_req1_snap1_dm2.pk).items()]
        [self.check_patch_case(case) for case in cases]

    def test_update_cohort_by_sjs_callback_status_finished(self):
        new_cohort: CohortResult = self.model_objects.create(**self.basic_data)
        data = {'request_job_status': 'finished',
                'group.id': '123456',
                'group.count': 10500}

        request = self.factory.patch(self.objects_url, data=data, format='json')
        force_authenticate(request, new_cohort.owner)
        response = self.__class__.update_view(request, **{self.model._meta.pk.name: new_cohort.uuid})
        response.render()

        self.assertEqual(response.data.get("request_job_status"), JobStatus.finished.value)
        self.assertEqual(response.data.get("fhir_group_id"), data['group.id'])
        self.assertEqual(response.data.get("result_size"), data['group.count'])

    def test_update_cohort_by_sjs_callback_status_failed(self):
        new_cohort: CohortResult = self.model_objects.create(**self.basic_data)
        data = {'request_job_status': 'error',
                'group.id': '',
                'group.count': 10500}

        request = self.factory.patch(self.objects_url, data=data, format='json')
        force_authenticate(request, new_cohort.owner)
        response = self.__class__.update_view(request, **{self.model._meta.pk.name: new_cohort.uuid})
        response.render()

        self.assertEqual(response.data.get("request_job_status"), JobStatus.failed.value)
        self.assertIsNotNone(response.data.get("request_job_fail_msg"))
        self.assertIsNotNone(response.data.get("request_job_duration"))

    def test_error_update_cohort_by_sjs_callback_invalid_status(self):
        invalid_status = 'INVALID_STATUS'
        case = self.basic_err_case.clone(data_to_update={'request_job_status': invalid_status})
        self.check_patch_case(case)

    @mock.patch('cohort.views.cohort_result.send_email_notif_about_large_cohort')
    def test_update_cohort_status_by_etl_callback(self, mock_send_email_notif: MagicMock):
        case = self.basic_case.clone(data_to_update={'request_job_status': 'finished'})
        mock_send_email_notif.side_effect = SMTPException("SMTP server error")
        self.check_patch_case(case)
        mock_send_email_notif.assert_called()
