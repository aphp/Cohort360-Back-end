from unittest import mock

from exporters.enums import ExportTypes
from exporters.tests.base_test import ExportersTestBase
from exporters.exporters.csv_exporter import CSVExporter


class TestCSVExporter(ExportersTestBase):
    def setUp(self):
        super().setUp()
        with mock.patch('exporters.exporters.base_exporter.ExportAPI'):
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

    def test_successfully_validate_export(self):
        export_data = dict(output_format=ExportTypes.CSV.value,
                           nominative=True,
                           motivation='motivation',
                           export_tables=[{"table_name": "table1",
                                           "cohort_result_source": self.cohort.pk
                                           },
                                          {"table_name": "person",
                                           "cohort_result_source": self.cohort.pk
                                           }
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
