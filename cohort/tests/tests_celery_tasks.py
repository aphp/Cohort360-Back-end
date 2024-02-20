from unittest import mock

from django.utils import timezone
from requests import Response
from rest_framework import status

from admin_cohort.types import JobStatus
from cohort.crb import AbstractCohortRequest
from cohort.models import DatedMeasure, CohortResult, Request, RequestQuerySnapshot, FeasibilityStudy
from cohort.models.dated_measure import GLOBAL_DM_MODE
from cohort.services.conf_cohort_job_api import JobServerResponse
from cohort.tasks import get_count_task, create_cohort_task, cancel_previously_running_dm_jobs, get_feasibility_count_task
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

        self.basic_count_response = {"success": True,
                                     "jobId": self.test_job_id,
                                     "status": "started"
                                     }
        self.failed_count_response = {"success": False,
                                      "status": "error",
                                      "err_msg": self.test_count_err_msg
                                      }
        self.resp_create_cohort_success = {"success": True,
                                           "jobId": self.test_job_id,
                                           "status": "started"
                                           }
        self.resp_create_cohort_failed = {"success": False,
                                          "status": "error",
                                          "err_msg": self.test_create_err_msg
                                          }

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

    @mock.patch('cohort.tasks.cohort_job_api')
    def test_get_count_task(self, mock_cohort_job_api):
        mock_cohort_job_api.post_count_cohort.return_value = JobServerResponse(**self.basic_count_response)
        get_count_task(auth_headers={},
                       json_query="{}",
                       dm_uuid=self.user1_req1_snap1_initial_dm.uuid)

        new_dm = DatedMeasure.objects.filter(pk=self.user1_req1_snap1_initial_dm.uuid,
                                             request_job_id=self.test_job_id).first()
        self.assertIsNotNone(new_dm)

    @mock.patch('cohort.tasks.celery_app.control.revoke')
    @mock.patch('cohort.tasks.cohort_job_api.cancel_job')
    def test_cancel_previously_running_dm_jobs_task(self, mock_cancel_job, mock_celery_revoke):
        mock_celery_revoke.return_value = None
        mock_cancel_job.return_value = JobStatus.cancelled
        cancel_previously_running_dm_jobs(dm_uuid=self.new_dm1.uuid)
        cancelled_dms = DatedMeasure.objects.exclude(uuid=self.new_dm1.uuid)\
                                            .filter(request_query_snapshot=self.user1_req_running_dms_snap1)

        for dm in cancelled_dms:
            self.assertEqual(dm.request_job_status, JobStatus.cancelled.value)

    @mock.patch('cohort.tasks.cohort_job_api.cancel_job')
    def test_error_on_cancel_previously_running_dm_jobs_task(self, mock_cancel_job):
        mock_cancel_job.side_effect = Exception("Error on calling to cancel running DMs")
        cancel_previously_running_dm_jobs(dm_uuid=self.new_dm2.uuid)
        failed_dm = DatedMeasure.objects.exclude(uuid=self.new_dm2.uuid)\
                                        .filter(request_query_snapshot=self.user1_req_running_dms_snap2)\
                                        .first()
        self.assertEqual(failed_dm.request_job_status, JobStatus.failed.value)

    @mock.patch('cohort.tasks.cohort_job_api')
    def test_get_count_global_task(self, mock_cohort_job_api):
        mock_cohort_job_api.post_count_cohort.return_value = JobServerResponse(**self.basic_count_response)
        get_count_task(auth_headers={},
                       json_query="{}",
                       dm_uuid=self.user1_req1_snap1_initial_global_dm.uuid)

        new_dm = DatedMeasure.objects.filter(pk=self.user1_req1_snap1_initial_global_dm.uuid,
                                             request_job_id=self.test_job_id).first()
        self.assertIsNotNone(new_dm)

    @mock.patch('cohort.tasks.cohort_job_api')
    def test_failed_get_count_task(self, mock_cohort_job_api):
        mock_cohort_job_api.post_count_cohort.return_value = JobServerResponse(**self.failed_count_response)
        get_count_task(auth_headers={},
                       json_query="{}",
                       dm_uuid=self.user1_req1_snap1_initial_dm.uuid)
        test_err_msg = "Error on getting count"
        new_dm = DatedMeasure.objects.filter(pk=self.user1_req1_snap1_initial_dm.uuid,
                                             request_job_status=JobStatus.failed,
                                             request_job_fail_msg=test_err_msg).first()
        self.assertIsNotNone(new_dm)

    @mock.patch('cohort.tasks.cohort_job_api')
    def test_create_cohort_task_for_small_cohort(self, mock_cohort_job_api):
        mock_cohort_job_api.post_create_cohort.return_value = JobServerResponse(**self.resp_create_cohort_success)
        create_cohort_task(auth_headers={},
                           json_query="{}",
                           cohort_uuid=self.small_cohort.uuid)

        new_cr = CohortResult.objects.filter(pk=self.small_cohort.pk,
                                             dated_measure=self.user1_req1_snap1_dm1,
                                             request_job_status=JobStatus.pending,
                                             request_job_id=self.test_job_id,
                                             ).first()
        self.assertIsNotNone(new_cr)

    @mock.patch('cohort.tasks.cohort_job_api')
    def test_create_cohort_task_for_large_cohort(self, mock_cohort_job_api):
        mock_cohort_job_api.post_create_cohort.return_value = JobServerResponse(**self.resp_create_cohort_success)
        create_cohort_task({}, "{}", self.large_cohort.uuid)

        new_cr = CohortResult.objects.filter(pk=self.large_cohort.pk,
                                             dated_measure=self.user1_req1_snap1_dm2,
                                             request_job_status=JobStatus.long_pending,
                                             request_job_id=self.test_job_id,
                                             ).first()
        self.assertIsNotNone(new_cr)

    @mock.patch('cohort.tasks.cohort_job_api')
    def test_failed_create_cohort_task(self, mock_cohort_job_api):
        mock_cohort_job_api.post_create_cohort.return_value = JobServerResponse(**self.resp_create_cohort_failed)
        create_cohort_task(auth_headers={},
                           json_query="{}",
                           cohort_uuid=self.small_cohort.uuid)

        create_err_msg = "Error in cohort creation task"
        new_cr = CohortResult.objects.filter(pk=self.small_cohort.pk,
                                             dated_measure=self.user1_req1_snap1_dm1,
                                             request_job_status=JobStatus.failed,
                                             request_job_fail_msg=create_err_msg,
                                             ).first()
        self.assertIsNotNone(new_cr)

    @mock.patch('cohort.crb.cohort_requests.abstract_cohort_request.accesses_service.user_can_access_at_least_one_target_perimeter_in_nomi')
    @mock.patch.object(AbstractCohortRequest, '_AbstractCohortRequest__headers_to_owner_entity')
    @mock.patch('cohort.crb.cohort_requests.count_feasibility.get_top_care_site_source_population')
    @mock.patch('cohort.crb.sjs_client.requests.post')
    def test_get_feasibility_count_task(self, mock_sjs_client_count, mock_top_care_site_source_population,
                                        mock_owner_entity, mock_is_nomi_access):
        mock_response = Response()
        mock_response.status_code = status.HTTP_200_OK
        mock_response._text = 'returned a jobId'
        mock_response._content = b'{"jobId": "some-job-uuid", "status": "running"}'
        mock_sjs_client_count.return_value = mock_response
        mock_top_care_site_source_population.return_value = '1111'
        mock_owner_entity.return_value = self.user1.username
        mock_is_nomi_access.return_value = True
        get_feasibility_count_task(fs_uuid=self.user1_feasibility_study.uuid,
                                   json_query='{"sourcePopulation": {"caresiteCohortList": [1111]}}',
                                   auth_headers={}
                                   )
        new_fs = FeasibilityStudy.objects.filter(pk=self.user1_feasibility_study.uuid,
                                                 request_job_id="some-job-uuid").first()
        self.assertIsNotNone(new_fs)
