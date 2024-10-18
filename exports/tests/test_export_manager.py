from unittest import TestCase, mock

from django.core.exceptions import ImproperlyConfigured

from exports.apps import ExportsConfig
from exports.models import Export
from exports.services.export_operators import load_available_exporters, DefaultExporter, ExportManager
from exports.tests.test_view_export_request import ExportsTests


class TestExportersLoader(TestCase):

    def setUp(self):
        super().setUp()

    def test_load_available_exporters(self):
        plain_type = "plain"
        ExportsConfig.EXPORTERS = [{"TYPE": plain_type,
                                    "EXPORTER_CLASS": "exports.services.export_operators.DefaultExporter"
                                    }]
        exporters = load_available_exporters()
        self.assertEqual(list(exporters.keys())[0], plain_type)
        self.assertEqual(list(exporters.values())[0], DefaultExporter)

    def test_error_load_available_exporters_no_exporters(self):
        ExportsConfig.EXPORTERS = []
        with self.assertRaises(ImproperlyConfigured):
            _ = load_available_exporters()

    def test_error_load_available_exporters_wrong_export_type(self):
        ExportsConfig.EXPORTERS = [{"TYPE": "wrong",
                                    "EXPORTER_CLASS": "exports.services.export_operators.DefaultExporter"
                                    }]
        with self.assertRaises(ImproperlyConfigured):
            _ = load_available_exporters()


class TestExportManager(ExportsTests):

    def setUp(self):
        super().setUp()
        self.basic_export_data = dict(output_format="plain",
                                      nominative=True,
                                      motivation='motivation')
        self.basic_export = Export.objects.create(**self.basic_export_data,
                                                  owner=self.user1)
        with mock.patch("exports.services.export_operators.load_available_exporters") as mock_load_available_exporters:
            mock_load_available_exporters.return_value = {"plain": DefaultExporter}
            self.export_manager = ExportManager()

    def test_validate(self):
        export_data = dict(output_format="plain",
                           nominative=True,
                           cohort_result_source=self.user1_cohort.uuid,
                           motivation='motivation',
                           export_tables=[{"table_name": "table1"}]
                           )
        with self.assertRaises(NotImplementedError):
            self.export_manager.validate(export_data=export_data, owner=self.user1)

    def test_handle_export(self):
        with self.assertRaises(NotImplementedError):
            self.export_manager.handle_export(export_id=self.basic_export.pk)
