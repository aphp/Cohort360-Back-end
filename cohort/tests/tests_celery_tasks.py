from unittest import mock
from unittest.mock import MagicMock

from django.test import TestCase

from accesses.models import Perimeter
from admin_cohort.tests.tests_tools import new_random_user
from admin_cohort.types import JobStatus
from cohort.models import DatedMeasure, CohortResult, Request, RequestQuerySnapshot, FeasibilityStudy, Folder
from cohort.models.dated_measure import GLOBAL_DM_MODE
from cohort.services.cohort_operators import DefaultCohortCounter, DefaultCohortCreator
from cohort.services.emails import send_email_notif_feasibility_report_requested, send_email_notif_error_feasibility_report, \
    send_email_notif_feasibility_report_ready
from cohort.tasks import count_cohort, create_cohort, cancel_previous_count_jobs, feasibility_study_count, send_feasibility_study_notification, \
    send_email_feasibility_report_ready, send_email_feasibility_report_error


class TasksTests(TestCase):
    def setUp(self):
        super(TasksTests, self).setUp()
        self.test_job_id = "job_id"
        self.test_task_id = "task_id"
        self.test_count_err_msg = "Error on getting count"
        self.test_create_err_msg = "Error in cohort creation task"

        self.main_perimeter = Perimeter.objects.create(name="Main Perimeter", level=1, cohort_id="1234")
        self.json_query = '{"sourcePopulation": {"caresiteCohortList": ["%s"]}}' % self.main_perimeter.cohort_id
        self.auth_headers = {'Authorization': 'Bearer XXXX', 'authorizationMethod': 'OIDC'}

        self.user1 = new_random_user()
        self.folder = Folder.objects.create(owner=self.user1, name="folder01")
        self.request = Request.objects.create(owner=self.user1,
                                              name="Request 01 with running DMs",
                                              description="Request with DMs started, pending",
                                              parent_folder=self.folder)
        self.req_snapshot = RequestQuerySnapshot.objects.create(owner=self.user1,
                                                                request=self.request,
                                                                serialized_query='{}')
        self.dm1 = DatedMeasure.objects.create(owner=self.user1,
                                               request_query_snapshot=self.req_snapshot)
        self.global_dm = DatedMeasure.objects.create(owner=self.user1,
                                                     request_query_snapshot=self.req_snapshot,
                                                     mode=GLOBAL_DM_MODE)
        self.cohort = CohortResult.objects.create(name="My small cohort",
                                                  description="with a small count",
                                                  owner=self.user1,
                                                  request_query_snapshot=self.req_snapshot,
                                                  dated_measure=self.dm1)

        self.req_snapshot2 = RequestQuerySnapshot.objects.create(owner=self.user1,
                                                                request=self.request,
                                                                serialized_query='{}')
        self.new_dm = DatedMeasure.objects.create(request_query_snapshot=self.req_snapshot2,
                                                  request_job_status=JobStatus.new,
                                                  owner=self.user1)
        self.started_dm = DatedMeasure.objects.create(request_query_snapshot=self.req_snapshot2,
                                                      request_job_status=JobStatus.started,
                                                      owner=self.user1)
        self.pending_dm = DatedMeasure.objects.create(request_query_snapshot=self.req_snapshot2,
                                                      request_job_status=JobStatus.pending,
                                                      owner=self.user1)

        self.req_snapshot3 = RequestQuerySnapshot.objects.create(owner=self.user1,
                                                                 request=self.request,
                                                                 serialized_query='{}')
        self.dm2 = DatedMeasure.objects.create(request_query_snapshot=self.req_snapshot3,
                                               request_job_status=JobStatus.new,
                                               owner=self.user1)
        self.started_dm2 = DatedMeasure.objects.create(request_query_snapshot=self.req_snapshot3,
                                                       request_job_status=JobStatus.started,
                                                       owner=self.user1)
        self.user1_feasibility_study = FeasibilityStudy.objects.create(owner=self.user1,
                                                                       request_query_snapshot=self.req_snapshot)
        self.cohort_counter_cls = f"{DefaultCohortCounter.__module__}.{DefaultCohortCounter.__qualname__}"
        self.cohort_creator_cls = f"{DefaultCohortCreator.__module__}.{DefaultCohortCreator.__qualname__}"

    def test_count_cohort_task(self):
        with self.assertRaises(NotImplementedError):
            count_cohort(dm_id=self.dm1.uuid,
                         json_query=self.json_query,
                         cohort_counter_cls=self.cohort_counter_cls,
                         auth_headers=self.auth_headers)

    def test_count_cohort_task_with_global_mode(self):
        with self.assertRaises(NotImplementedError):
            count_cohort(dm_id=self.global_dm.uuid,
                         json_query=self.json_query,
                         cohort_counter_cls=self.cohort_counter_cls,
                         auth_headers=self.auth_headers,
                         global_estimate=True)

    def test_create_cohort_task(self):
        with self.assertRaises(NotImplementedError):
            create_cohort(cohort_id=self.cohort.uuid,
                          json_query=self.json_query,
                          cohort_creator_cls=self.cohort_creator_cls,
                          auth_headers=self.auth_headers)

    def test_feasibility_study_count_task(self):
        success = feasibility_study_count(fs_id=self.user1_feasibility_study.uuid,
                                          json_query=self.json_query,
                                          cohort_counter_cls=self.cohort_counter_cls,
                                          auth_headers=self.auth_headers)
        self.assertTrue(success)

    def test_feasibility_email_notification_tasks(self):
        fs_id = self.user1_feasibility_study.uuid
        cases = [{"task": send_feasibility_study_notification,
                  "args": (True, fs_id),
                  "notification_to_send": send_email_notif_feasibility_report_requested
                  },
                 {"task": send_feasibility_study_notification,
                  "args": (False, fs_id),
                  "notification_to_send": send_email_notif_error_feasibility_report
                  },
                 {"task": send_email_feasibility_report_ready,
                  "args": (fs_id,),
                  "notification_to_send": send_email_notif_feasibility_report_ready
                  },
                 {"task": send_email_feasibility_report_error,
                  "args": (fs_id,),
                  "notification_to_send": send_email_notif_error_feasibility_report
                  }]
        for case in cases:
            self.check_task_case(case=case)

    @mock.patch('cohort.tasks.send_email_notification')
    def check_task_case(self, mock_send_notif: MagicMock, case: dict):
        task, args, notification_to_send = case['task'], case['args'], case['notification_to_send']
        task(*args)
        mock_send_notif.assert_called_once()
        self.assertTrue(mock_send_notif.call_args.kwargs.get('notification') is notification_to_send)

    @mock.patch('cohort.tasks.celery_app.control.revoke')
    def test_cancel_previous_count_jobs_task(self, mock_celery_revoke):
        mock_celery_revoke.return_value = None
        cancel_previous_count_jobs(dm_id=self.new_dm.uuid,
                                   cohort_counter_cls=self.cohort_counter_cls)
        cancelled_dms = DatedMeasure.objects.exclude(uuid=self.new_dm.uuid)\
                                            .filter(request_query_snapshot=self.req_snapshot2)

        for dm in cancelled_dms:
            self.assertEqual(dm.request_job_status, JobStatus.cancelled.value)

    @mock.patch.object(DefaultCohortCounter, 'cancel_job')
    def test_error_cancel_previous_count_jobs_task(self, mock_cancel_job):
        mock_cancel_job.side_effect = Exception("Error cancelling running DMs")
        cancel_previous_count_jobs(dm_id=self.dm2.uuid,
                                   cohort_counter_cls=self.cohort_counter_cls)
        failed_dm = DatedMeasure.objects.exclude(uuid=self.dm2.uuid)\
                                        .filter(request_query_snapshot=self.req_snapshot3)\
                                        .first()
        self.assertEqual(failed_dm.request_job_status, JobStatus.failed.value)
