from exporters.enums import ExportTypes
from exporters.tests.base_test import ExportersTestBase
from exporters.csv_exporter import CSVExporter


class TestCSVExporter(ExportersTestBase):
    def setUp(self):
        super().setUp()
        self.exporter = CSVExporter()

    def test_error_validate_export_not_owned_cohort(self):
        export_data = dict(output_format=ExportTypes.CSV.value,
                           cohort_id=self.cohort3.fhir_group_id,
                           nominative=True,
                           motivation='motivation',
                           tables=[{"omop_table_name": "table1"}])
        with self.assertRaises(ValueError):
            self.exporter.validate(export_data=export_data, owner=self.csv_exporter_user)

    def test_error_validate_export_not_nominative(self):
        export_data = dict(output_format=ExportTypes.CSV.value,
                           cohort_id=self.cohort.fhir_group_id,
                           nominative=False,
                           motivation='motivation',
                           tables=[{"omop_table_name": "table1"}])
        with self.assertRaises(ValueError):
            self.exporter.validate(export_data=export_data, owner=self.csv_exporter_user)


class TestCSVExporterWithOldModels(TestCSVExporter):

    def test_successfully_validate_export(self):
        export_data = dict(output_format=ExportTypes.CSV.value,
                           cohort_id=self.cohort.fhir_group_id,
                           nominative=True,
                           motivation='motivation',
                           tables=[{"omop_table_name": "table1"}])
        self.exporter.validate(export_data=export_data, owner=self.csv_exporter_user)


class TestCSVExporterWithNewModels(TestCSVExporter):

    def test_successfully_validate_export(self):
        export_data = dict(output_format=ExportTypes.CSV.value,
                           nominative=True,
                           motivation='motivation',
                           export_tables=[{"name": "table1", "cohort_result_source": self.cohort.pk},
                                          {"name": "person", "cohort_result_source": self.cohort.pk}]
                           )
        self.exporter.validate(export_data=export_data, owner=self.csv_exporter_user)

    def test_error_validate_export_with_multiple_source_cohorts(self):
        export_data = dict(output_format=ExportTypes.CSV.value,
                           nominative=True,
                           motivation='motivation',
                           export_tables=[{"name": "table1", "cohort_result_source": self.cohort.pk},
                                          {"name": "person", "cohort_result_source": self.cohort2.pk}]
                           )
        with self.assertRaises(AssertionError):
            self.exporter.validate(export_data=export_data, owner=self.csv_exporter_user)
