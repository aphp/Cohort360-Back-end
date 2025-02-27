from unittest import mock
from unittest.mock import MagicMock

from django.test import TestCase
from requests import RequestException
from rest_framework import status

from admin_cohort.types import JobStatus
from exporters.apis.infra_api import InfraAPI


class TestInfraAPI(TestCase):
    def setUp(self):
        super().setUp()
        self.api_conf = {
            "INFRA_API": {
                "API_URL": 'https://infra-api.fr/api',
                "AUTH_TOKEN": "hadoop-token",
                "TASK_STATUS_ENDPOINT": '/hadoop/task_status',
                "CREATE_DB_ENDPOINT": '/hadoop/create_db',
                "ALTER_DB_ENDPOINT": '/hadoop/chown_db',
            },
        }
        with mock.patch('exporters.apis.base.ExportersConfig') as mock_exports_config:
            mock_exports_config.THIRD_PARTY_API_CONF = self.api_conf
            self.infra_api = InfraAPI()


    @mock.patch('exporters.apis.base.requests')
    def test_get_export_job_status(self, mock_requests):
        mock_response = MagicMock()
        mock_response.json.return_value = {'task_status': 'FinishedSuccessfully'}
        mock_requests.get.return_value = mock_response
        job_status = self.infra_api.get_job_status(job_id='123456')
        self.assertEqual(job_status, JobStatus.finished)
        mock_requests.get.assert_called_once_with(url='https://infra-api.fr/api/hadoop/task_status',
                                                  params={'task_uuid': '123456',
                                                          'return_out_logs': True,
                                                          'return_err_logs': True},
                                                  headers={'auth-token': 'hadoop-token'})

    @mock.patch('exporters.apis.base.requests')
    def test_get_db_creation_job_status(self, mock_requests):
        mock_response = MagicMock()
        mock_response.json.return_value = {'task_status': 'Running'}
        mock_requests.get.return_value = mock_response
        job_status = self.infra_api.get_job_status(job_id='123456',)
        self.assertEqual(job_status, JobStatus.started)
        mock_requests.get.assert_called_once_with(url='https://infra-api.fr/api/hadoop/task_status',
                                                  params={'task_uuid': '123456',
                                                          'return_out_logs': True,
                                                          'return_err_logs': True},
                                                  headers={'auth-token': 'hadoop-token'})

    @mock.patch('exporters.apis.infra_api.requests')
    def test_create_db(self, mock_requests):
        mock_response = MagicMock()
        mock_response.json.return_value = {'task_id': '123456'}
        mock_requests.post.return_value = mock_response
        task_id = self.infra_api.create_db(name='some_db_name', location='/dir1/dir2')
        self.assertEqual(task_id, '123456')
        mock_requests.post.assert_called_once_with(url='https://infra-api.fr/api/hadoop/create_db',
                                                   params={'name': 'some_db_name',
                                                           'location': '/dir1/dir2',
                                                           'if_not_exists': True},
                                                   headers={'auth-token': 'hadoop-token'})

    @mock.patch('exporters.apis.infra_api.requests')
    def test_change_db_ownership(self, mock_requests):
        mock_response = MagicMock()
        mock_response.status_code = status.HTTP_200_OK
        mock_response.json.return_value = {'status': 'success', 'ret_code': 0}
        mock_requests.post.return_value = mock_response
        self.infra_api.change_db_ownership(location='/dir1/dir2', db_user='future_owner')
        mock_requests.post.assert_called_once_with(url='https://infra-api.fr/api/hadoop/chown_db',
                                                   params={'location': '/dir1/dir2',
                                                           'uid': 'future_owner',
                                                           'gid': 'hdfs',
                                                           'recursive': True},
                                                   headers={'auth-token': 'hadoop-token'})

    @mock.patch('exporters.apis.infra_api.requests')
    def test_error_change_db_ownership(self, mock_requests):
        mock_response = MagicMock()
        mock_response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        mock_response.json.return_value = {'status': 'error', 'ret_code': 1}
        mock_requests.post.return_value = mock_response
        with self.assertRaises(RequestException):
            self.infra_api.change_db_ownership(location='/dir1/dir2', db_user='future_owner')
