from exporters.base_exporter import BaseExporter
from exporters.enums import ExportTypes
from exporters.tests.base_test import ExportersTestBase


class TestBaseExporter(ExportersTestBase):

    def setUp(self) -> None:
        super().setUp()
        self.person_table_name = "person"
        self.cohorts = [self.cohort, self.cohort2]
        self.exporter = BaseExporter()

    def test_validate_tables_data_all_tables_have_source_cohort(self):
        # all tables have a linked source cohort
        tables_data = [{"name": self.person_table_name, "cohort_result_source": self.cohorts[0].uuid},
                       {"name": "other_table_01", "cohort_result_source": self.cohorts[1].uuid}]
        check = self.exporter.validate_tables_data(tables_data=tables_data)
        self.assertTrue(check)

    def test_validate_tables_data_only_person_table_has_source_cohort(self):
        # only `person` table has a linked source cohort, the other tables don't
        tables_data = [{"name": self.person_table_name, "cohort_result_source": self.cohorts[0].uuid},
                       {"name": "table_01"},
                       {"name": "table_02"}]
        check = self.exporter.validate_tables_data(tables_data=tables_data)
        self.assertTrue(check)

    def test_validate_tables_data_one_table_with_source_cohort(self):
        # tables data is valid if the source cohort is provided within the table data
        tables_data = [{"name": "table_01", "cohort_result_source": self.cohorts[0].uuid}]
        check = self.exporter.validate_tables_data(tables_data=tables_data)
        self.assertTrue(check)

    def test_validate_tables_data_missing_source_cohort_for_person_table(self):
        # tables tada is not valid if the `person` table dict is in the list but missing the source cohort
        tables_data = [{"name": self.person_table_name},
                       {"name": "table_01", "cohort_result_source": self.cohorts[0].uuid}]
        with self.assertRaises(ValueError):
            self.exporter.validate_tables_data(tables_data=tables_data)

    def test_validate_tables_data_with_only_person_table_without_source_cohort(self):
        # tables data is not valid if the `person` table has no source cohort
        tables_data = [{"name": self.person_table_name}]
        with self.assertRaises(ValueError):
            self.exporter.validate_tables_data(tables_data=tables_data)

    def test_validate_tables_data_all_tables_without_source_cohort(self):
        # tables data is not valid if the `person` table has no source cohort
        tables_data = [{"name": "table_01"},
                       {"name": "table_02"}]
        with self.assertRaises(ValueError):
            self.exporter.validate_tables_data(tables_data=tables_data)

    def test_complete_export_data(self):
        export_data = dict(output_format=ExportTypes.CSV.value,
                           target_unix_account=self.unix_account.pk,
                           nominative=True,
                           motivation='motivation\nover\nmulti lines',
                           tables=[{"omop_table_name": "table1"}]
                           )
        self.exporter.complete_data(export_data=export_data, owner=self.csv_exporter_user)
        self.assertIn("owner", export_data)
        self.assertIn("target_name", export_data)
        self.assertIn("target_location", export_data)
        self.assertNotIn("\n", export_data["motivation"])
