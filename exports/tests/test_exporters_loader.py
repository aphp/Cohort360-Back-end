from unittest import mock

from django.core.exceptions import ImproperlyConfigured

from admin_cohort.tests.tests_tools import TestCaseWithDBs
from exporters.exporters.csv_exporter import CSVExporter
from exporters.exporters.hive_exporter import HiveExporter
from exporters.exporters.xlsx_exporter import XLSXExporter
from exports.apps import ExportsConfig
from exports.services.export import load_available_exporters


ExportTypes = ExportsConfig.ExportTypes


class TestExportersLoader(TestCaseWithDBs):

    def setUp(self):
        super().setUp()

    def test_error_load_available_exporters_wrong_export_type(self):
        mock_exports_list = [{"TYPE": "wrong",
                              "EXPORTER_CLASS": "exports.services.export_operators.DefaultExporter"
                              }]
        with mock.patch('exports.services.export.EXPORTERS', mock_exports_list):
            with self.assertRaises(ImproperlyConfigured):
                _ = load_available_exporters()

    def test_error_load_available_exporters_no_exporters(self):
        with mock.patch('exports.services.export.EXPORTERS', []):
            with self.assertRaises(ImproperlyConfigured):
                _ = load_available_exporters()

    def test_load_available_exporters(self):
        exporters = load_available_exporters()
        for export_type in (ExportTypes.CSV, ExportTypes.HIVE, ExportTypes.XLSX):
            self.assertIn(export_type.value, exporters.keys())
        for exporter in (CSVExporter, HiveExporter, XLSXExporter):
            self.assertIn(exporter, exporters.values())


