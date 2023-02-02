from unittest import mock
from unittest.mock import MagicMock

from django.utils import timezone

from admin_cohort.types import JobStatus
from cohort.crb_responses import CRBCountResponse, CRBCohortResponse
from cohort.models import DatedMeasure, CohortResult
from cohort.models.dated_measure import GLOBAL_DM_MODE
from cohort.tasks import get_count_task, create_cohort_task
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

        self.basic_count_response = dict(count=self.test_count,
                                         fhir_datetime=self.test_datetime,
                                         fhir_job_id=self.test_job_id,
                                         job_duration=self.test_job_duration,
                                         success=True,
                                         fhir_job_status=JobStatus.finished,
                                         count_max=self.test_count,
                                         count_min=self.test_count)

        self.resp_create_cohort_success = {"success": True,
                                           "fhir_job_id": self.test_job_id,
                                           }
        self.resp_create_cohort_failed = {"success": False,
                                          "fhir_job_status": JobStatus.failed,
                                          "err_msg": self.test_create_err_msg
                                          }

    @mock.patch('cohort.tasks.cohort_job_api')
    def test_get_count_task(self, mock_cohort_job_api):
        mock_cohort_job_api.post_count_cohort.return_value = CRBCountResponse(**self.basic_count_response)
        get_count_task(auth_headers={},
                       json_query="{}",
                       dm_uuid=self.user1_req1_snap1_initial_dm.uuid)

        new_dm = DatedMeasure.objects.filter(pk=self.user1_req1_snap1_initial_dm.uuid,
                                             measure_min__isnull=True,
                                             measure_max__isnull=True,
                                             measure=self.test_count,
                                             fhir_datetime=self.test_datetime,
                                             request_job_duration=self.test_job_duration,
                                             request_job_status=JobStatus.finished,
                                             request_job_id=self.test_job_id,
                                             ).first()
        self.assertIsNotNone(new_dm)

    @mock.patch('cohort.tasks.cohort_job_api')
    def test_get_count_global_task(self, mock_cohort_job_api):
        mock_cohort_job_api.post_count_cohort.return_value = CRBCountResponse(**self.basic_count_response)
        get_count_task(auth_headers={},
                       json_query="{}",
                       dm_uuid=self.user1_req1_snap1_initial_global_dm.uuid)

        new_dm = DatedMeasure.objects.filter(pk=self.user1_req1_snap1_initial_global_dm.uuid,
                                             measure__isnull=True,
                                             measure_min=self.test_count,
                                             measure_max=self.test_count,
                                             fhir_datetime=self.test_datetime,
                                             request_job_duration=self.test_job_duration,
                                             request_job_status=JobStatus.finished,
                                             request_job_id=self.test_job_id,
                                             ).first()
        self.assertIsNotNone(new_dm)

    @mock.patch('cohort.tasks.cohort_job_api')
    def test_failed_get_count_task(self, mock_cohort_job_api):
        mock_cohort_job_api.post_count_cohort.return_value = CRBCountResponse(fhir_job_id=self.test_job_id,
                                                                              job_duration=self.test_job_duration,
                                                                              fhir_job_status=JobStatus.failed,
                                                                              success=False,
                                                                              err_msg=self.test_count_err_msg)
        get_count_task(auth_headers={},
                       json_query="{}",
                       dm_uuid=self.user1_req1_snap1_initial_dm.uuid)
        test_err_msg = "Error on getting count"
        new_dm = DatedMeasure.objects.filter(pk=self.user1_req1_snap1_initial_dm.uuid,
                                             measure__isnull=True,
                                             measure_min__isnull=True,
                                             measure_max__isnull=True,
                                             request_job_id=self.test_job_id,
                                             request_job_duration=self.test_job_duration,
                                             request_job_status=JobStatus.failed,
                                             request_job_fail_msg=test_err_msg,
                                             ).first()
        self.assertIsNotNone(new_dm)

    @mock.patch('cohort.tasks.cohort_job_api')
    def test_create_cohort_task_for_small_cohort(self, mock_cohort_job_api):
        mock_cohort_job_api.post_create_cohort.return_value = CRBCohortResponse(**self.resp_create_cohort_success)
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
        mock_cohort_job_api.post_create_cohort.return_value = CRBCohortResponse(**self.resp_create_cohort_success)
        create_cohort_task({}, "{}", self.large_cohort.uuid)

        new_cr = CohortResult.objects.filter(pk=self.large_cohort.pk,
                                             dated_measure=self.user1_req1_snap1_dm2,
                                             request_job_status=JobStatus.long_pending,
                                             request_job_id=self.test_job_id,
                                             ).first()
        self.assertIsNotNone(new_cr)

    @mock.patch('cohort.tasks.cohort_job_api')
    def test_failed_create_cohort_task(self, mock_cohort_job_api):
        mock_cohort_job_api.post_create_cohort.return_value = CRBCohortResponse(**self.resp_create_cohort_failed)
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
