from unittest import mock
from unittest.mock import MagicMock

from django.utils import timezone

from admin_cohort.types import JobStatus
from cohort.crb_responses import CRBCountResponse, CRBCohortResponse
from cohort.models import DatedMeasure, GLOBAL_DM_MODE, CohortResult
from cohort.tasks import get_count_task, create_cohort_task
from cohort.tests.tests_view_dated_measure import DatedMeasuresTests


class TasksTests(DatedMeasuresTests):
    def setUp(self):
        super(TasksTests, self).setUp()
        self.test_count = 102
        self.test_datetime = timezone.now().replace(tzinfo=timezone.utc)
        self.test_job_id = "job_id"
        self.test_task_id = "task_id"
        self.test_job_duration = 1000
        self.test_job_status_finished = JobStatus.finished

        self.user1_req1_snap1_empty_dm = DatedMeasure.objects.create(
            owner=self.user1,
            request_query_snapshot=self.user1_req1_snap1,
            count_task_id=self.test_task_id,
            request_job_status=JobStatus.pending
        )
        self.user1_req1_snap1_empty_global_dm = DatedMeasure.objects.create(
            owner=self.user1,
            request_query_snapshot=self.user1_req1_snap1,
            count_task_id=self.test_task_id,
            request_job_status=JobStatus.pending,
            mode=GLOBAL_DM_MODE,
        )

        self.user1_req1_snap1_empty_cohort = CohortResult.objects.create(
            owner=self.user1,
            request_query_snapshot=self.user1_req1_snap1,
            name="My empty cohort",
            description="so empty",
            create_task_id="task_id",
            request_job_status=JobStatus.pending,
            dated_measure=self.user1_req1_snap1_empty_dm
        )

        self.basic_response_common_data = dict(
            count=self.test_count,
            fhir_datetime=self.test_datetime,
            fhir_job_id=self.test_job_id,
            job_duration=self.test_job_duration,
            success=True,
            fhir_job_status=self.test_job_status_finished
        )
        self.basic_count_data_response = {
            **self.basic_response_common_data,
            "count_max": self.test_count,
            "count_min": self.test_count
        }
        self.basic_create_data_response = {
            **self.basic_response_common_data,
            'group_id': self.test_job_id,
        }

    @mock.patch('cohort.tasks.cohort_job_api')
    def test_get_count_task(self, mock_cohort_job_api: MagicMock):
        mock_cohort_job_api.post_count_cohort.return_value = CRBCountResponse(
            **self.basic_count_data_response
        )
        get_count_task({}, "{}", self.user1_req1_snap1_empty_dm.uuid)

        new_dm = DatedMeasure.objects.filter(
            pk=self.user1_req1_snap1_empty_dm.uuid,
            measure_min__isnull=True,
            measure_max__isnull=True,
            measure=self.test_count,
            fhir_datetime=self.test_datetime,
            request_job_duration=self.test_job_duration,
            request_job_status=self.test_job_status_finished,
            request_job_id=self.test_job_id,
            # count_task_id=self.user1_req1_snap1_empty_dm.count_task_id
        ).first()
        self.assertIsNotNone(new_dm)

    @mock.patch('cohort.tasks.cohort_job_api')
    def test_get_count_global_task(self, mock_cohort_job_api):
        mock_cohort_job_api.post_count_cohort.return_value = CRBCountResponse(
            **self.basic_count_data_response
        )
        get_count_task({}, "{}", self.user1_req1_snap1_empty_global_dm.uuid)

        new_dm = DatedMeasure.objects.filter(
            pk=self.user1_req1_snap1_empty_global_dm.uuid,
            measure__isnull=True,
            measure_min=self.test_count,
            measure_max=self.test_count,
            fhir_datetime=self.test_datetime,
            request_job_duration=self.test_job_duration,
            request_job_status=self.test_job_status_finished,
            request_job_id=self.test_job_id,
            # count_task_id=self.user1_req1_snap1_empty_dm.count_task_id
        ).first()
        self.assertIsNotNone(new_dm)

    @mock.patch('cohort.tasks.cohort_job_api')
    def test_failed_get_count_task(self, mock_cohort_job_api):
        test_err_msg = "Error"
        job_status = JobStatus.failed

        mock_cohort_job_api.post_count_cohort.return_value = CRBCountResponse(
            fhir_job_id=self.test_job_id,
            job_duration=self.test_job_duration,
            fhir_job_status=job_status,
            success=False,
            err_msg=test_err_msg,
        )

        get_count_task({}, "{}", self.user1_req1_snap1_empty_dm.uuid)

        new_dm = DatedMeasure.objects.filter(
            pk=self.user1_req1_snap1_empty_dm.uuid,
            measure__isnull=True,
            measure_min__isnull=True,
            measure_max__isnull=True,
            request_job_id=self.test_job_id,
            request_job_duration=self.test_job_duration,
            request_job_status=job_status,
            request_job_fail_msg=test_err_msg,
            # count_task_id=self.user1_req1_snap1_empty_dm.count_task_id
        ).first()

        # while calling Fhir API
        self.assertIsNotNone(new_dm)
        self.assertIsNone(new_dm.measure)
        self.assertIsNone(new_dm.fhir_datetime)

    @mock.patch('cohort.tasks.cohort_job_api')
    def test_create_cohort_task(self, mock_cohort_job_api):
        mock_cohort_job_api.post_create_cohort.return_value = CRBCohortResponse(
            **self.basic_create_data_response
        )
        create_cohort_task({}, "{}", self.user1_req1_snap1_empty_cohort.uuid)

        new_cr = CohortResult.objects.filter(
            pk=self.user1_req1_snap1_empty_cohort.pk,
            dated_measure=self.user1_req1_snap1_empty_dm,
            # dated_measure__measure=self.test_count,
            # dated_measure__measure_min__isnull=True,
            # dated_measure__measure_max__isnull=True,
            # dated_measure__fhir_datetime=self.test_datetime,
            # dated_measure__request_job_duration=self.test_job_duration,
            # dated_measure__request_job_status=self.test_job_status_finished,
            # dated_measure__request_job_id=self.test_job_id,
            request_job_status=self.test_job_status_finished,
            fhir_group_id=self.test_job_id,
            request_job_id=self.test_job_id,
            request_job_duration=self.test_job_duration,
        ).first()
        self.assertIsNotNone(new_cr)

    @mock.patch('cohort.tasks.cohort_job_api')
    def test_failed_create_cohort_task(self, mock_cohort_job_api):
        test_err_msg = "Error"
        job_status = JobStatus.failed

        mock_cohort_job_api.post_create_cohort.return_value = CRBCohortResponse(fhir_job_id=self.test_job_id,
                                                                                job_duration=self.test_job_duration,
                                                                                fhir_job_status=job_status,
                                                                                success=False,
                                                                                err_msg=test_err_msg)
        create_cohort_task({}, "{}", self.user1_req1_snap1_empty_cohort.uuid)

        new_cr = CohortResult.objects.filter(
            pk=self.user1_req1_snap1_empty_cohort.pk,
            dated_measure=self.user1_req1_snap1_empty_dm,
            # dated_measure__measure__isnull=True,
            # dated_measure__measure_min__isnull=True,
            # dated_measure__measure_max__isnull=True,
            # dated_measure__fhir_datetime__isnull=True,
            # dated_measure__request_job_duration=self.test_job_duration,
            # dated_measure__request_job_status=JobStatus.failed.value,
            # dated_measure__request_job_fail_msg=test_err_msg,
            # dated_measure__request_job_id=self.test_job_id,
            request_job_status=JobStatus.failed.value,
            request_job_fail_msg=test_err_msg,
            fhir_group_id="",
            request_job_id=self.test_job_id,
            request_job_duration=self.test_job_duration,
        ).first()
        # TODO: I could not find how to test that intermediate state of
        #  request_job_status is set to 'started'
        # while calling Fhir API
        self.assertIsNotNone(new_cr)
