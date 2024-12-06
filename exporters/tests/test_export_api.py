from unittest import mock
from unittest.mock import MagicMock
import uuid

from django.test import TestCase

from admin_cohort.types import JobStatus
from exporters.apis.export_api import ExportAPI
from exporters.enums import ExportTypes


class TestExportAPI(TestCase):
    def setUp(self):
        super().setUp()
        self.api_conf = {
            "EXPORT_API": {
                "API_URL": 'https://export-api.fr/api',
                "AUTH_TOKEN": "bigdata-token",
                "TASK_STATUS_ENDPOINT": '/task_status',
            },
        }
        with mock.patch('exporters.apis.base.ExportersConfig') as mock_exports_config:
            mock_exports_config.THIRD_PARTY_API_CONF = self.api_conf
            self.export_api = ExportAPI()

    @mock.patch('exporters.apis.export_api.requests')
    def test_launch_export_csv(self, mock_requests):
        mock_response = MagicMock()
        mock_response.json.return_value = {'task_id': '123456'}
        mock_requests.post.return_value = mock_response
        params = {'export_type': ExportTypes.CSV.value, 'api_param': 'value'}
        task_id = self.export_api.launch_export(export_id=uuid.uuid4(), params=params)
        self.assertEqual(task_id, '123456')
        mock_requests.post.assert_called_once()

    @mock.patch('exporters.apis.export_api.requests')
    def test_launch_export_hive(self, mock_requests):
        mock_response = MagicMock()
        mock_response.json.return_value = {'task_id': '123456'}
        mock_requests.post.return_value = mock_response
        params = {'export_type': ExportTypes.HIVE.value, 'api_param': 'value'}
        task_id = self.export_api.launch_export(export_id=uuid.uuid4(), params=params)
        self.assertEqual(task_id, '123456')
        mock_requests.post.assert_called_once()

    @mock.patch('exporters.apis.base.requests')
    def test_get_export_job_status(self, mock_requests):
        mock_response = MagicMock()
        mock_response.json.return_value = {'task_status': 'FinishedSuccessfully'}
        mock_requests.get.return_value = mock_response
        job_status = self.export_api.get_job_status(job_id='123456')
        self.assertEqual(job_status, JobStatus.finished)
        mock_requests.get.assert_called_once_with(url='https://export-api.fr/api/task_status',
                                                  params={'task_uuid': '123456',
                                                          'return_out_logs': True,
                                                          'return_err_logs': True},
                                                  headers={'auth-token': 'bigdata-token'})
