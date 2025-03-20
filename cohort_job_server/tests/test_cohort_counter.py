from unittest import mock

from requests import Response, HTTPError
from rest_framework import status

from admin_cohort.types import JobStatus
from cohort.models import DatedMeasure, FeasibilityStudy
from cohort_job_server.cohort_counter import CohortCounter
from cohort_job_server.sjs_api import CohortCount, FeasibilityCount, SJSClient
from cohort_job_server.tests.base import BaseTest


class CohortCounterTest(BaseTest):

    def setUp(self):
        super().setUp()

        with mock.patch('cohort_job_server.base_operator.CohortJobServerConfig') as mock_app_conf:
            mock_app_conf.API_USERNAMES = []
            self.cohort_counter = CohortCounter()

        self.count_cohort_success_resp_content = str.encode('{"status": "STARTED", "jobId": "%s"}' % self.test_job_id)
        self.count_cohort_failed_resp_content = str.encode('{"status": "ERROR", "err_msg": "%s"}' % self.test_err_msg)
        self.dm_global = DatedMeasure.objects.create(request_query_snapshot=self.snapshot, owner=self.user, mode="Global")
        self.fs = FeasibilityStudy.objects.create(owner=self.user, request_query_snapshot=self.snapshot)

    @mock.patch.object(CohortCount, 'launch')
    def test_successfully_launch_dated_measure_count(self, mock_launch):
        response = Response()
        response.status_code = status.HTTP_200_OK
        response._content = self.count_cohort_success_resp_content
        mock_launch.return_value = response
        self.cohort_counter.launch_dated_measure_count(self.dm.pk, self.json_query, self.auth_headers)
        mock_launch.assert_called_once()
        self.dm.refresh_from_db()
        self.assertEqual(self.dm.request_job_status, JobStatus.started.value)
        self.assertEqual(self.dm.request_job_id, self.test_job_id)
        
    @mock.patch('cohort_job_server.cohort_counter.CohortCount')
    def test_successfully_launch_dated_measure_count_with_stage_details(self, mock_cohort_count_class):
        # Setup mock CohortCount instance
        mock_cohort_count_instance = mock.MagicMock()
        mock_cohort_count_class.return_value = mock_cohort_count_instance
        
        # Setup mock response
        response = Response()
        response.status_code = status.HTTP_200_OK
        response._content = self.count_cohort_success_resp_content
        
        # Setup mock SJSRequester
        with mock.patch.object(self.cohort_counter, 'sjs_requester') as mock_sjs_requester:
            mock_sjs_requester.launch_request.return_value = response
            
            # Call the method with stage_details
            stage_details = "detailed"
            self.cohort_counter.launch_dated_measure_count(self.dm.pk, self.json_query, self.auth_headers, stage_details=stage_details)
            
            # Verify that CohortCount was initialized with the stage_details parameter
            mock_cohort_count_class.assert_called_once()
            self.assertEqual(mock_cohort_count_class.call_args.kwargs['stage_details'], stage_details)
            
            # Verify that launch_request was called with the CohortCount instance
            mock_sjs_requester.launch_request.assert_called_once_with(mock_cohort_count_instance)

    @mock.patch.object(CohortCount, 'launch')
    def test_error_launch_dated_measure_count(self, mock_launch):
        mock_launch.side_effect = HTTPError(self.test_err_msg)
        self.cohort_counter.launch_dated_measure_count(self.dm.pk, self.json_query, self.auth_headers)
        mock_launch.assert_called_once()
        self.dm.refresh_from_db()
        self.assertEqual(self.dm.request_job_status, JobStatus.failed.value)
        self.assertEqual(self.dm.request_job_fail_msg, self.test_err_msg)

    @mock.patch.object(FeasibilityCount, 'launch')
    def test_successfully_launch_feasibility_study_count(self, mock_launch):
        response = Response()
        response.status_code = status.HTTP_200_OK
        response._content = self.count_cohort_success_resp_content
        mock_launch.return_value = response
        resp_success = self.cohort_counter.launch_feasibility_study_count(self.fs.pk, self.json_query, self.auth_headers)
        mock_launch.assert_called_once()
        self.assertTrue(resp_success)
        self.fs.refresh_from_db()
        self.assertEqual(self.fs.request_job_status, JobStatus.started.value)
        self.assertEqual(self.fs.request_job_id, self.test_job_id)

    @mock.patch.object(SJSClient, 'delete')
    def test_successfully_cancel_job(self, mock_delete_job):
        response = Response()
        response.status_code = status.HTTP_200_OK
        response._content = str.encode('{"status": "KILLED"}')
        mock_delete_job.return_value = response
        s = self.cohort_counter.cancel_job(self.test_job_id)
        mock_delete_job.assert_called_once_with(self.test_job_id)
        self.assertEqual(s, JobStatus.cancelled)

    def test_successfully_handle_patch_dated_measure(self):
        count = 9999
        patch_data = {'request_job_status': 'FINISHED',
                      'count': count}
        self.cohort_counter.handle_patch_dated_measure(dm=self.dm, data=patch_data)
        self.assertTrue('count' not in patch_data)
        self.assertEqual(patch_data['measure'], count)
        self.assertEqual(patch_data['request_job_status'], JobStatus.finished.value)
        self.assertIsNotNone(patch_data['request_job_duration'])
        
    def test_successfully_handle_patch_dated_measure_with_extra(self):
        count = 9999
        extra_data = {'details': {'group1': 50, 'group2': 75}}
        patch_data = {'request_job_status': 'FINISHED',
                      'count': count,
                      'extra': extra_data}
        self.cohort_counter.handle_patch_dated_measure(dm=self.dm, data=patch_data)
        self.assertTrue('count' not in patch_data)
        self.assertEqual(patch_data['measure'], count)
        self.assertEqual(patch_data['extra'], extra_data)
        self.assertEqual(patch_data['request_job_status'], JobStatus.finished.value)
        self.assertIsNotNone(patch_data['request_job_duration'])

    def test_successfully_handle_patch_global_dated_measure(self):
        measure_min, measure_max = 100, 200
        patch_data = {'request_job_status': 'FINISHED',
                      'minimum': measure_min,
                      'maximum': measure_max}
        self.cohort_counter.handle_patch_dated_measure(dm=self.dm_global, data=patch_data)
        self.assertTrue('minimum' not in patch_data)
        self.assertTrue('maximum' not in patch_data)
        self.assertEqual(patch_data['measure_min'], measure_min)
        self.assertEqual(patch_data['measure_max'], measure_max)
        self.assertEqual(patch_data['request_job_status'], JobStatus.finished.value)
        self.assertIsNotNone(patch_data['request_job_duration'])

    def test_handle_patch_dated_measure_failed(self):
        patch_data = {'request_job_status': 'ERROR',
                      'message': self.test_err_msg}
        self.cohort_counter.handle_patch_dated_measure(dm=self.dm, data=patch_data)
        self.assertTrue('message' not in patch_data)
        self.assertEqual(patch_data['request_job_fail_msg'], self.test_err_msg)
        self.assertEqual(patch_data['request_job_status'], JobStatus.failed.value)
        self.assertIsNotNone(patch_data['request_job_duration'])

    def test_handle_patch_dated_measure_invalid_status(self):
        patch_data = {'request_job_status': 'WRONG_STATUS',
                      'count': '9999'}
        with self.assertRaises(ValueError):
            self.cohort_counter.handle_patch_dated_measure(dm=self.dm, data=patch_data)

    def test_successfully_handle_patch_feasibility_study(self):
        count = 100
        extra = {'11': 55, '12': 75}
        patch_data = {'request_job_status': 'FINISHED',
                      'count': count,
                      'extra': extra}
        self.cohort_counter.handle_patch_feasibility_study(fs=self.fs, data=patch_data)
        self.assertTrue('count' not in patch_data)
        self.assertTrue('extra' not in patch_data)
        self.assertEqual(patch_data['total_count'], count)
        self.assertEqual(patch_data['request_job_status'], JobStatus.finished.value)

    def test_handle_patch_feasibility_study_failed(self):
        patch_data = {'request_job_status': 'ERROR',
                      'message': self.test_err_msg}
        self.cohort_counter.handle_patch_feasibility_study(fs=self.fs, data=patch_data)
        self.assertTrue('message' not in patch_data)
        self.assertEqual(patch_data['request_job_fail_msg'], self.test_err_msg)
        self.assertEqual(patch_data['request_job_status'], JobStatus.failed.value)

    def test_handle_patch_feasibility_study_invalid_status(self):
        patch_data = {'request_job_status': 'WRONG_STATUS',
                      'count': '9999',
                      'extra': {}}
        with self.assertRaises(ValueError):
            self.cohort_counter.handle_patch_feasibility_study(fs=self.fs, data=patch_data)
