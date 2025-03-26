from unittest import mock

from django.conf import settings
from requests import Response, HTTPError
from rest_framework import status

from admin_cohort.types import JobStatus
from cohort.models import CohortResult
from cohort_job_server.cohort_creator import CohortCreator
from cohort_job_server.query_executor_api import CohortCreate
from cohort_job_server.tests.base import BaseTest


class CohortCreatorTest(BaseTest):

    def setUp(self):
        super().setUp()

        with mock.patch('cohort_job_server.base_operator.CohortJobServerConfig') as mock_app_conf:
            mock_app_conf.API_USERNAMES = []
            self.cohort_creator = CohortCreator()

        self.small_count_value = settings.COHORT_SIZE_LIMIT // 2
        self.large_count_value = 2 * settings.COHORT_SIZE_LIMIT
        self.create_cohort_success_resp_content = str.encode('{"status": "STARTED", "jobId": "%s"}' % self.test_job_id)
        self.cohort = CohortResult.objects.create(request_query_snapshot=self.snapshot,
                                                  dated_measure=self.dm,
                                                  owner=self.user)

    @mock.patch.object(CohortCreate, 'launch')
    def test_successfully_launch_small_cohort_creation(self, mock_launch):
        self.cohort.dated_measure.measure = self.small_count_value
        self.cohort.dated_measure.save()
        response = Response()
        response.status_code = status.HTTP_200_OK
        response._content = self.create_cohort_success_resp_content
        mock_launch.return_value = response
        self.cohort_creator.launch_cohort_creation(self.cohort.pk, self.json_query, self.auth_headers)
        mock_launch.assert_called_once()
        self.cohort.refresh_from_db()
        self.assertEqual(self.cohort.request_job_status, JobStatus.pending.value)
        self.assertEqual(self.cohort.request_job_id, self.test_job_id)

    @mock.patch.object(CohortCreate, 'launch')
    def test_successfully_launch_large_cohort_creation(self, mock_launch):
        self.cohort.dated_measure.measure = self.large_count_value
        self.cohort.dated_measure.save()
        response = Response()
        response.status_code = status.HTTP_200_OK
        response._content = self.create_cohort_success_resp_content
        mock_launch.return_value = response
        self.cohort_creator.launch_cohort_creation(self.cohort.pk, self.json_query, self.auth_headers)
        mock_launch.assert_called_once()
        self.cohort.refresh_from_db()
        self.assertEqual(self.cohort.request_job_status, JobStatus.long_pending.value)
        self.assertEqual(self.cohort.request_job_id, self.test_job_id)

    @mock.patch.object(CohortCreate, 'launch')
    def test_error_launch_cohort_creation(self, mock_launch):
        mock_launch.side_effect = HTTPError(self.test_err_msg)
        self.cohort_creator.launch_cohort_creation(self.cohort.pk, self.json_query, self.auth_headers)
        mock_launch.assert_called_once()
        self.cohort.refresh_from_db()
        self.assertEqual(self.cohort.request_job_status, JobStatus.failed.value)
        self.assertEqual(self.cohort.request_job_fail_msg, self.test_err_msg)

    def test_successfully_handle_patch_cohort(self):
        group_id, group_count = '12345', 555
        patch_data = {'request_job_status': 'FINISHED',
                      'group.id': group_id,
                      'group.count': group_count}
        self.cohort_creator.handle_patch_cohort(cohort=self.cohort, data=patch_data)
        self.assertTrue('group.id' not in patch_data)
        self.assertTrue('group.count' not in patch_data)
        self.assertEqual(patch_data['group_id'], group_id)
        self.assertEqual(self.cohort.dated_measure.measure, group_count)
        self.assertEqual(patch_data['request_job_status'], JobStatus.finished.value)
        self.assertIsNotNone(patch_data['request_job_duration'])

    def test_handle_patch_cohort_failed(self):
        patch_data = {'request_job_status': 'ERROR',
                      'message': self.test_err_msg}
        self.cohort_creator.handle_patch_cohort(cohort=self.cohort, data=patch_data)
        self.assertTrue('message' not in patch_data)
        self.assertEqual(patch_data['request_job_status'], JobStatus.failed.value)
        self.assertEqual(patch_data['request_job_fail_msg'], self.test_err_msg)
        self.assertIsNotNone(patch_data['request_job_duration'])

    def test_handle_patch_cohort_invalid_status(self):
        patch_data = {'request_job_status': 'WRONG_STATUS',
                      'group.id': '12345'}
        with self.assertRaises(ValueError):
            self.cohort_creator.handle_patch_cohort(cohort=self.cohort, data=patch_data)

    @mock.patch('cohort_job_server.cohort_creator.notify_large_cohort_ready.apply_async')
    @mock.patch('cohort_job_server.cohort_creator._logger.info')
    def test_handle_cohort_post_update_query_executor_callback(self, mock_logger, mock_notify):
        mock_logger.return_value = None
        mock_notify.return_value = None
        patch_data = {'request_job_status': 'FINISHED',
                      'group.id': '12345',
                      'group.count': '777'}
        self.cohort_creator.handle_cohort_post_update(cohort=self.cohort, data=patch_data)
        mock_logger.assert_called_once()
        mock_notify.assert_not_called()

    @mock.patch('cohort_job_server.cohort_creator.notify_large_cohort_ready.apply_async')
    @mock.patch('cohort_job_server.cohort_creator._logger.info')
    def test_handle_cohort_post_update_etl_callback(self, mock_logger, mock_notify):
        mock_logger.return_value = None
        mock_notify.return_value = None
        patch_data = {'request_job_status': 'FINISHED'}
        self.cohort_creator.handle_cohort_post_update(cohort=self.cohort, data=patch_data)
        mock_logger.assert_not_called()
        mock_notify.assert_called_once()
