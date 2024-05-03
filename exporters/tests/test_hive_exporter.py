from unittest import mock

from requests import RequestException

from admin_cohort.types import JobStatus
from exporters.hive_exporter import HiveExporter
from exporters.tests.base_test import ExportersTestBase


class TestHiveExporter(ExportersTestBase):
    def setUp(self):
        super().setUp()
        with mock.patch('exporters.base_exporter.InfraAPI'):
            self.exporter = HiveExporter()
            self.mock_export_api = self.exporter.export_api

    def test_successfully_create_db(self):
        self.mock_export_api.create_db.return_value = "some-job-id"
        self.mock_export_api.get_job_status.return_value = JobStatus.finished
        self.exporter.create_db(export=self.hive_export)
        self.mock_export_api.create_db.assert_called_once()
        self.mock_export_api.get_job_status.assert_called_once()

    def test_error_create_db(self):
        self.mock_export_api.create_db.return_value = "some-job-id"
        self.mock_export_api.get_job_status.return_value = JobStatus.failed
        with self.assertRaises(RequestException):
            self.exporter.create_db(export=self.hive_export)

    def test_successfully_change_db_ownership(self):
        self.mock_export_api.change_db_ownership.return_value = None
        self.exporter.change_db_ownership(export=self.hive_export, db_user=self.hive_exporter_user)
        self.mock_export_api.change_db_ownership.assert_called_once()

    def test_error_change_db_ownership(self):
        self.mock_export_api.change_db_ownership.side_effect = RequestException()
        with self.assertRaises(RequestException):
            self.exporter.change_db_ownership(export=self.hive_export, db_user=self.hive_exporter_user)
            self.mock_export_api.change_db_ownership.assert_called_once()

    def test_successfully_conclude_export(self):
        self.mock_export_api.change_db_ownership.return_value = None
        self.exporter.conclude_export(export=self.hive_export)
        self.mock_export_api.change_db_ownership.assert_called_once()

    @mock.patch('exporters.base_exporter.notify_export_failed.delay')
    def test_error_conclude_export(self, mock_notify_export_failed):
        self.mock_export_api.change_db_ownership.side_effect = RequestException()
        self.exporter.conclude_export(export=self.hive_export)
        mock_notify_export_failed.assert_called_once()
