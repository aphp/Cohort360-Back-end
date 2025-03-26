from unittest import mock

from requests import RequestException

from admin_cohort.types import JobStatus
from exporters.exporters.hive_exporter import HiveExporter
from exporters.tests.base_test import ExportersTestBase


class TestHiveExporter(ExportersTestBase):
    def setUp(self):
        super().setUp()
        self.person_table_name = "person"
        self.cohorts = [self.cohort, self.cohort2]
        with mock.patch('exporters.exporters.base_exporter.HadoopAPI'):
            self.exporter = HiveExporter()
            self.mock_infra_api = self.exporter.hadoop_api
            self.mock_infra_api.required_table = "person"

    def test_validate_tables_data_all_tables_have_source_cohort(self):
        # all tables have a linked source cohort
        tables_data = [{"table_name": self.person_table_name, "cohort_result_source": self.cohorts[0].uuid},
                       {"table_name": "other_table_01", "cohort_result_source": self.cohorts[1].uuid}]
        check = self.exporter.validate_tables_data(tables_data=tables_data)
        self.assertTrue(check)

    def test_validate_tables_data_only_person_table_has_source_cohort(self):
        # only `person` table has a linked source cohort, the other tables don't
        tables_data = [{"table_name": "table_01"},
                       {"table_name": self.person_table_name, "cohort_result_source": self.cohorts[0].uuid},
                       {"table_name": "table_02"}]
        check = self.exporter.validate_tables_data(tables_data=tables_data)
        self.assertTrue(check)

    def test_validate_tables_data_one_table_with_source_cohort(self):
        # tables data is valid if the source cohort is provided within the table data
        tables_data = [{"table_name": "table_01", "cohort_result_source": self.cohorts[0].uuid}]
        check = self.exporter.validate_tables_data(tables_data=tables_data)
        self.assertTrue(check)

    def test_validate_tables_data_missing_source_cohort_for_person_table(self):
        # tables tada is not valid if the `person` table dict is in the list but missing the source cohort
        tables_data = [{"table_name": self.person_table_name},
                       {"table_name": "table_01", "cohort_result_source": self.cohorts[0].uuid}]
        with self.assertRaises(ValueError):
            self.exporter.validate_tables_data(tables_data=tables_data)

    def test_validate_tables_data_with_only_person_table_without_source_cohort(self):
        # tables data is not valid if the `person` table has no source cohort
        tables_data = [{"table_name": self.person_table_name}]
        with self.assertRaises(ValueError):
            self.exporter.validate_tables_data(tables_data=tables_data)

    def test_validate_tables_data_all_tables_without_source_cohort_nor_person_table(self):
        # tables data is not valid if the `person` table has no source cohort
        tables_data = [{"table_name": "table_01"},
                       {"table_name": "table_02"}]
        with self.assertRaises(ValueError):
            self.exporter.validate_tables_data(tables_data=tables_data)

    def test_successfully_create_db(self):
        self.mock_infra_api.create_db.return_value = "some-job-id"
        self.mock_infra_api.get_job_status.return_value = JobStatus.finished
        self.exporter.create_db(export=self.hive_export)
        self.mock_infra_api.create_db.assert_called_once()
        self.mock_infra_api.get_job_status.assert_called_once()

    def test_error_create_db(self):
        self.mock_infra_api.create_db.return_value = "some-job-id"
        self.mock_infra_api.get_job_status.return_value = JobStatus.failed
        with self.assertRaises(RequestException):
            self.exporter.create_db(export=self.hive_export)

    def test_successfully_change_db_ownership(self):
        self.mock_infra_api.change_db_ownership.return_value = None
        self.exporter.change_db_ownership(export=self.hive_export, db_user=self.hive_user)
        self.mock_infra_api.change_db_ownership.assert_called_once()

    def test_error_change_db_ownership(self):
        self.mock_infra_api.change_db_ownership.side_effect = RequestException()
        with self.assertRaises(RequestException):
            self.exporter.change_db_ownership(export=self.hive_export, db_user=self.hive_user)
            self.mock_infra_api.change_db_ownership.assert_called_once()

    def test_successfully_conclude_export(self):
        self.mock_infra_api.change_db_ownership.return_value = None
        self.exporter.conclude_export(export=self.hive_export)
        self.mock_infra_api.change_db_ownership.assert_called_once()

    @mock.patch('exporters.exporters.base_exporter.notify_export_failed.delay')
    def test_error_conclude_export(self, mock_notify_export_failed):
        self.mock_infra_api.change_db_ownership.side_effect = RequestException()
        self.exporter.conclude_export(export=self.hive_export)
        mock_notify_export_failed.assert_called_once()
