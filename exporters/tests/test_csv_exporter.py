from unittest import mock

from admin_cohort.types import JobStatus
from exporters.enums import ExportTypes
from exporters.tests.base_test import ExportersTestBase
from exporters.csv_exporter import CSVExporter


class TestCSVExporter(ExportersTestBase):
    def setUp(self):
        super().setUp()
        with mock.patch('exporters.base_exporter.InfraAPI'):
            self.exporter = CSVExporter()
            self.mock_export_api = self.exporter.export_api

    def test_error_validate_export_not_owned_cohort(self):
        export_data = dict(output_format=ExportTypes.CSV.value,
                           cohort_result_source=self.cohort3.uuid,
                           nominative=True,
                           motivation='motivation',
                           export_tables=[{"table_name": "table1"}])
        with self.assertRaises(ValueError):
            self.exporter.validate(export_data=export_data, owner=self.csv_exporter_user)

    def test_error_validate_export_not_nominative(self):
        export_data = dict(output_format=ExportTypes.CSV.value,
                           cohort_result_source=self.cohort.uuid,
                           nominative=False,
                           motivation='motivation',
                           export_tables=[{"table_name": "table1"}])
        with self.assertRaises(ValueError):
            self.exporter.validate(export_data=export_data, owner=self.csv_exporter_user)

    @mock.patch('exporters.base_exporter.notify_export_succeeded.delay')
    @mock.patch('exporters.base_exporter.notify_export_received.delay')
    def test_successfully_handle_export(self, mock_notify_export_received, mock_notify_export_succeeded):
        self.mock_export_api.required_table = "person"
        self.mock_export_api.target_environment = "target_environment"
        self.mock_export_api.launch_export.return_value = "some-job-id"
        self.mock_export_api.get_job_status.return_value = JobStatus.finished
        self.exporter.handle_export(export=self.csv_export)
        mock_notify_export_received.assert_called_once()
        mock_notify_export_succeeded.assert_called_once()
        self.assertEqual(self.csv_export.request_job_status, JobStatus.finished.value)
        self.assertIsNotNone(self.csv_export.request_job_id)
        self.assertIsNotNone(self.csv_export.request_job_duration)

    def test_successfully_validate_export(self):
        export_data = dict(output_format=ExportTypes.CSV.value,
                           nominative=True,
                           motivation='motivation',
                           cohort_result_source=self.cohort.pk,
                           export_tables=[{"table_name": "table1"},
                                          {"table_name": "person"}
                                          ]
                           )
        self.exporter.validate(export_data=export_data, owner=self.csv_exporter_user)

    def test_error_validate_export_without_source_cohort(self):
        export_data = dict(output_format=ExportTypes.CSV.value,
                           nominative=True,
                           motivation='motivation',
                           export_tables=[{"table_name": "table1"},
                                          {"table_name": "person"}
                                          ]
                           )
        with self.assertRaises(ValueError):
            self.exporter.validate(export_data=export_data, owner=self.csv_exporter_user)
