from unittest import mock

from admin_cohort.types import JobStatus
from exporters.tests.base_test import ExportersTestBase
from exporters.xlsx_exporter import XLSXExporter


class TestXLSXExporter(ExportersTestBase):
    def setUp(self):
        super().setUp()
        with mock.patch('exporters.base_exporter.InfraAPI'):
            self.xlsx_exporter = XLSXExporter()
            self.mock_export_api = self.xlsx_exporter.export_api

    @mock.patch('exporters.base_exporter.notify_export_succeeded.delay')
    @mock.patch('exporters.base_exporter.notify_export_received.delay')
    def test_successfully_handle_export(self, mock_notify_export_received, mock_notify_export_succeeded):
        self.mock_export_api.required_table = "person"
        self.mock_export_api.target_environment = "target_environment"
        self.mock_export_api.launch_export.return_value = "some-job-id"
        self.mock_export_api.get_job_status.return_value = JobStatus.finished
        self.xlsx_exporter.handle_export(export=self.xlsx_export)
        mock_notify_export_received.assert_called_once()
        mock_notify_export_succeeded.assert_called_once()
        self.mock_export_api.launch_export.assert_called_once()
        api_call_params = self.mock_export_api.launch_export.call_args[1]['params']
        self.assertTrue(api_call_params.get('export_in_one_table'))
