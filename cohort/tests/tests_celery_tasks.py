from unittest import mock

from django.utils import timezone
from requests import Response
from rest_framework import status

from accesses.models import Perimeter
from admin_cohort.types import JobStatus
from cohort.job_server_api.cohort_requests import CohortCreate, CohortCount, CohortCountAll
from cohort.job_server_api.cohort_requests.count_feasibility import CohortCountFeasibility
from cohort.models import DatedMeasure, CohortResult, Request, RequestQuerySnapshot, FeasibilityStudy
from cohort.models.dated_measure import GLOBAL_DM_MODE
from cohort.tasks import count_cohort, create_cohort, cancel_previous_count_jobs, feasibility_study_count
from cohort.tests.tests_view_dated_measure import DatedMeasuresTests


class TasksTests(DatedMeasuresTests):
    def setUp(self):
        super(TasksTests, self).setUp()
        self.test_count = 102
        self.test_small_count = 7500
        self.test_large_count = 25_000
        self.test_datetime = timezone.now()
        self.test_job_id = "job_id"
        self.test_task_id = "task_id"
        self.test_group_id = "group_id"
        self.test_job_duration = 1000
        self.test_count_err_msg = "Error on getting count"
        self.test_create_err_msg = "Error in cohort creation task"

        self.main_perimeter = Perimeter.objects.create(name="Main Perimeter", level=1, cohort_id="1234")
        self.json_query = '{"sourcePopulation": {"caresiteCohortList": ["%s"]}}' % self.main_perimeter.cohort_id
        self.auth_headers = {'Authorization': 'Bearer XXXX', 'authorizationMethod': 'OIDC'}

        self.user1_req1_snap1_initial_dm = DatedMeasure.objects.create(owner=self.user1,
                                                                       request_query_snapshot=self.user1_req1_snap1,
                                                                       )

        self.user1_req1_snap1_initial_global_dm = DatedMeasure.objects.create(
                                                                        owner=self.user1,
                                                                        request_query_snapshot=self.user1_req1_snap1,
                                                                        mode=GLOBAL_DM_MODE)

        self.user1_req1_snap1_dm1 = DatedMeasure.objects.create(owner=self.user1,
                                                                request_query_snapshot=self.user1_req1_snap1,
                                                                count_task_id=self.test_task_id,
                                                                request_job_status=JobStatus.finished,
                                                                measure=self.test_small_count)

        self.user1_req1_snap1_dm2 = DatedMeasure.objects.create(owner=self.user1,
                                                                request_query_snapshot=self.user1_req1_snap1,
                                                                count_task_id=self.test_task_id,
                                                                request_job_status=JobStatus.finished,
                                                                measure=self.test_large_count)

        self.small_cohort = CohortResult.objects.create(name="My small cohort",
                                                        description="with a small count",
                                                        owner=self.user1,
                                                        request_query_snapshot=self.user1_req1_snap1,
                                                        dated_measure=self.user1_req1_snap1_dm1)

        self.large_cohort = CohortResult.objects.create(name="My large cohort",
                                                        description="with a large count",
                                                        owner=self.user1,
                                                        request_query_snapshot=self.user1_req1_snap1,
                                                        dated_measure=self.user1_req1_snap1_dm2)

        self.count_cohort_success_resp_content = str.encode('{"status": "started", "jobId": "%s"}' % self.test_job_id)
        self.count_cohort_failed_resp_content = str.encode('{"status": "error", "err_msg": "%s"}' % self.test_count_err_msg)

        self.create_cohort_success_resp_content = str.encode('{"status": "started", "jobId": "%s"}' % self.test_job_id)
        self.create_cohort_failed_resp_content = str.encode('{"status": "error", "err_msg": "%s"}' % self.test_create_err_msg)

        self.req_with_running_dms1 = Request.objects.create(owner=self.user1,
                                                            name="Request 01 with running DMs",
                                                            description="Request with DMs started, pending",
                                                            parent_folder=self.user1_folder1)

        self.req_with_running_dms2 = Request.objects.create(owner=self.user1,
                                                            name="Request 02 with running DMs",
                                                            description="Request with DMs started, pending",
                                                            parent_folder=self.user1_folder1)

        self.user1_req_running_dms_snap1 = RequestQuerySnapshot.objects.create(owner=self.user1,
                                                                               request=self.req_with_running_dms1,
                                                                               serialized_query='{}')

        self.new_dm1 = DatedMeasure.objects.create(request_query_snapshot=self.user1_req_running_dms_snap1,
                                                   request_job_status=JobStatus.new,
                                                   owner=self.user1)
        self.started_dm1 = DatedMeasure.objects.create(request_query_snapshot=self.user1_req_running_dms_snap1,
                                                       request_job_status=JobStatus.started,
                                                       owner=self.user1)
        self.pending_dm1 = DatedMeasure.objects.create(request_query_snapshot=self.user1_req_running_dms_snap1,
                                                       request_job_status=JobStatus.pending,
                                                       owner=self.user1)

        self.user1_req_running_dms_snap2 = RequestQuerySnapshot.objects.create(owner=self.user1,
                                                                               request=self.req_with_running_dms2,
                                                                               serialized_query='{}')

        self.new_dm2 = DatedMeasure.objects.create(request_query_snapshot=self.user1_req_running_dms_snap2,
                                                   request_job_status=JobStatus.new,
                                                   owner=self.user1)
        self.started_dm2 = DatedMeasure.objects.create(request_query_snapshot=self.user1_req_running_dms_snap2,
                                                       request_job_status=JobStatus.started,
                                                       owner=self.user1)
        self.user1_feasibility_study = FeasibilityStudy.objects.create(owner=self.user1,
                                                                       request_query_snapshot=self.user1_req_running_dms_snap1)

    @mock.patch.object(CohortCount, 'action')
    def test_count_cohort_task(self, mock_action):
        response = Response()
        response.status_code = status.HTTP_200_OK
        response._content = self.count_cohort_success_resp_content
        mock_action.return_value = response
        count_cohort(auth_headers=self.auth_headers,
                     json_query=self.json_query,
                     dm_id=self.user1_req1_snap1_initial_dm.uuid)

        new_dm = DatedMeasure.objects.filter(pk=self.user1_req1_snap1_initial_dm.uuid,
                                             request_job_id=self.test_job_id).first()
        self.assertIsNotNone(new_dm)

    @mock.patch('cohort.tasks.celery_app.control.revoke')
    @mock.patch('cohort.tasks.cancel_job')
    def test_cancel_previously_running_dm_jobs_task(self, mock_cancel_job, mock_celery_revoke):
        mock_celery_revoke.return_value = None
        mock_cancel_job.return_value = JobStatus.cancelled
        cancel_previous_count_jobs(dm_id=self.new_dm1.uuid)
        cancelled_dms = DatedMeasure.objects.exclude(uuid=self.new_dm1.uuid)\
                                            .filter(request_query_snapshot=self.user1_req_running_dms_snap1)

        for dm in cancelled_dms:
            self.assertEqual(dm.request_job_status, JobStatus.cancelled.value)

    @mock.patch('cohort.tasks.cancel_job')
    def test_error_on_cancel_previously_running_dm_jobs_task(self, mock_cancel_job):
        mock_cancel_job.side_effect = Exception("Error on calling to cancel running DMs")
        cancel_previous_count_jobs(dm_id=self.new_dm2.uuid)
        failed_dm = DatedMeasure.objects.exclude(uuid=self.new_dm2.uuid)\
                                        .filter(request_query_snapshot=self.user1_req_running_dms_snap2)\
                                        .first()
        self.assertEqual(failed_dm.request_job_status, JobStatus.failed.value)

    @mock.patch.object(CohortCountAll, 'action')
    def test_get_count_global_task(self, mock_action):
        response = Response()
        response.status_code = status.HTTP_200_OK
        response._content = self.count_cohort_success_resp_content
        mock_action.return_value = response
        count_cohort(auth_headers=self.auth_headers,
                     json_query=self.json_query,
                     dm_id=self.user1_req1_snap1_initial_global_dm.uuid)

        new_dm = DatedMeasure.objects.filter(pk=self.user1_req1_snap1_initial_global_dm.uuid,
                                             request_job_id=self.test_job_id).first()
        self.assertIsNotNone(new_dm)

    @mock.patch.object(CohortCount, 'action')
    def test_failed_count_cohort_task(self, mock_action):
        mock_action.return_value = None
        count_cohort(auth_headers=self.auth_headers,
                     json_query="{}",
                     dm_id=self.user1_req1_snap1_initial_dm.uuid)
        new_dm = DatedMeasure.objects.filter(pk=self.user1_req1_snap1_initial_dm.uuid,
                                             request_job_status=JobStatus.failed).first()
        self.assertIsNotNone(new_dm)

    @mock.patch.object(CohortCreate, 'action')
    def test_create_cohort_task_for_small_cohort(self, mock_action):
        response = Response()
        response.status_code = status.HTTP_200_OK
        response._content = self.create_cohort_success_resp_content
        mock_action.return_value = response
        create_cohort(auth_headers=self.auth_headers,
                      json_query=self.json_query,
                      cohort_id=self.small_cohort.uuid)

        new_cr = CohortResult.objects.filter(pk=self.small_cohort.pk,
                                             dated_measure=self.user1_req1_snap1_dm1,
                                             request_job_status=JobStatus.pending,
                                             request_job_id=self.test_job_id,
                                             ).first()
        self.assertIsNotNone(new_cr)

    @mock.patch.object(CohortCreate, 'action')
    def test_create_cohort_task_for_large_cohort(self, mock_action):
        response = Response()
        response.status_code = status.HTTP_200_OK
        response._content = self.create_cohort_success_resp_content
        mock_action.return_value = response
        create_cohort(self.auth_headers, self.json_query, self.large_cohort.uuid)

        new_cr = CohortResult.objects.filter(pk=self.large_cohort.pk,
                                             dated_measure=self.user1_req1_snap1_dm2,
                                             request_job_status=JobStatus.long_pending,
                                             request_job_id=self.test_job_id,
                                             ).first()
        self.assertIsNotNone(new_cr)

    @mock.patch.object(CohortCreate, 'action')
    def test_failed_create_cohort_task(self, mock_action):
        mock_action.return_value = None
        create_cohort(auth_headers=self.auth_headers,
                      json_query="{}",
                      cohort_id=self.small_cohort.uuid)

        new_cr = CohortResult.objects.filter(pk=self.small_cohort.pk,
                                             dated_measure=self.user1_req1_snap1_dm1,
                                             request_job_status=JobStatus.failed
                                             ).first()
        self.assertIsNotNone(new_cr)

    @mock.patch.object(CohortCountFeasibility, 'action')
    def test_get_feasibility_count_task(self, mock_action):
        response = Response()
        response.status_code = status.HTTP_200_OK
        response._content = self.count_cohort_success_resp_content
        mock_action.return_value = response
        feasibility_study_count(fs_id=self.user1_feasibility_study.uuid,
                                json_query=self.json_query,
                                auth_headers=self.auth_headers
                                )
        new_fs = FeasibilityStudy.objects.filter(pk=self.user1_feasibility_study.uuid,
                                                 request_job_id=self.test_job_id).first()
        self.assertIsNotNone(new_fs)
