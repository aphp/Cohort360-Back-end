from unittest import mock

from requests import RequestException

from exporters.exporters.base_exporter import BaseExporter
from exporters.enums import ExportTypes
from exporters.tests.base_test import ExportersTestBase
from exports.models import Export, ExportTable


class TestBaseExporter(ExportersTestBase):
    def setUp(self) -> None:
        super().setUp()
        self.api_conf = {
            "HADOOP_API": {
                "API_URL": "https://hadoop-api.fr/api",
                "AUTH_TOKEN": "hadoop-token",
                "TASK_STATUS_ENDPOINT": "/hadoop/task_status",
                "CREATE_DB_ENDPOINT": "/hadoop/create_db",
                "ALTER_DB_ENDPOINT": "/hadoop/chown_db",
            },
            "EXPORT_API": {
                "API_URL": "https://export-api.fr/api",
                "AUTH_TOKEN": "bigdata-token",
                "TASK_STATUS_ENDPOINT": "/task_status",
            },
        }
        with mock.patch("exporters.apis.base.ExportersConfig") as mock_exports_config:
            mock_exports_config.THIRD_PARTY_API_CONF = self.api_conf
            self.exporter = BaseExporter()

    def test_complete_export_data(self):
        export_data = dict(
            output_format=ExportTypes.HIVE.value,
            datalab=self.datalab.pk,
            nominative=True,
            motivation="motivation\nover\nmultiple\nlines",
            export_tables=[{"table_name": "table1", "cohort_result_source": self.cohort.uuid}],
        )
        self.exporter.complete_data(export_data=export_data, owner=self.csv_exporter_user)
        self.assertIn("owner", export_data)
        self.assertIn("target_name", export_data)
        self.assertIn("target_location", export_data)
        self.assertNotIn("\n", export_data["motivation"])

    def _build_datalab_export(self, patient_table_name: str) -> Export:
        export = Export.objects.create(
            owner=self.csv_exporter_user,
            target_location="target_location",
            target_name="target_name",
            nominative=True,
            output_format=ExportTypes.HIVE.value,
            datalab=self.datalab,
        )
        ExportTable.objects.create(export=export, name=patient_table_name, cohort_result_source=self.cohort)
        ExportTable.objects.create(export=export, name="death_date_insee", cohort_result_source=self.cohort)
        return export

    def test_send_export_succeeds_when_patient_table_capitalized(self):
        export = self._build_datalab_export(patient_table_name="Patient")
        with mock.patch.object(self.exporter.export_api, "launch_export", return_value="job-id") as mock_launch:
            self.exporter.send_export(export=export, params={})
        mock_launch.assert_called_once()
        tables_sent = [t["tableName"] for t in mock_launch.call_args.kwargs["params"]["tablesToExport"]]
        self.assertIn("Patient", tables_sent)
        self.assertIn("death_date_insee", tables_sent)

    @mock.patch.object(BaseExporter, "confirm_export_succeeded")
    @mock.patch.object(BaseExporter, "finalize_export")
    @mock.patch.object(BaseExporter, "wait_for_export_job")
    @mock.patch.object(BaseExporter, "send_export", return_value="job-id")
    def test_handle_export_finalizes_before_success(self, mock_send, mock_wait, mock_finalize, mock_succeeded):
        # finalize_export (where file permissions are set) must run BEFORE the success notification,
        # so the user is never told an export is ready while its files are still unreadable.
        export = self._build_datalab_export(patient_table_name="Patient")
        manager = mock.Mock()
        manager.attach_mock(mock_finalize, "finalize")
        manager.attach_mock(mock_succeeded, "succeeded")

        self.exporter.handle_export(export=export, params={})

        mock_finalize.assert_called_once_with(export=export)
        mock_succeeded.assert_called_once_with(export=export)
        self.assertEqual([call[0] for call in manager.mock_calls], ["finalize", "succeeded"])

    @mock.patch.object(BaseExporter, "mark_export_as_failed")
    @mock.patch.object(BaseExporter, "confirm_export_succeeded")
    @mock.patch.object(BaseExporter, "finalize_export", side_effect=RequestException("chown failed"))
    @mock.patch.object(BaseExporter, "wait_for_export_job")
    @mock.patch.object(BaseExporter, "send_export", return_value="job-id")
    def test_handle_export_marks_failed_when_finalize_fails(self, mock_send, mock_wait, mock_finalize, mock_succeeded, mock_failed):
        # A failure to finalize (e.g. the ownership transfer) must mark the export as failed and never
        # report success.
        export = self._build_datalab_export(patient_table_name="Patient")

        self.exporter.handle_export(export=export, params={})

        mock_finalize.assert_called_once_with(export=export)
        mock_failed.assert_called_once()
        mock_succeeded.assert_not_called()

    def test_send_export_adds_patient_identifier_and_its_filter(self):
        # Ref #3397: without the filter, patient__identifier carries every identifier, not only the IPP.
        export = self._build_datalab_export(patient_table_name="Patient")
        with mock.patch.object(self.exporter.export_api, "launch_export", return_value="job-id") as mock_launch:
            self.exporter.send_export(export=export, params={})
        params = mock_launch.call_args.kwargs["params"]
        tables_sent = [t["tableName"] for t in params["tablesToExport"]]
        self.assertEqual(tables_sent, ["Patient", "death_date_insee", "patient__identifier"])
        self.assertEqual(
            params["filters"],
            [
                {
                    "tableName": "patient__identifier",
                    "expression": "system= 'https://aphp.fr/meta/Patient/ipp' and use= 'official'",
                }
            ],
        )

    def test_send_export_does_not_duplicate_a_requested_patient_identifier(self):
        export = self._build_datalab_export(patient_table_name="Patient")
        ExportTable.objects.create(export=export, name="patient__identifier", cohort_result_source=self.cohort)
        with mock.patch.object(self.exporter.export_api, "launch_export", return_value="job-id") as mock_launch:
            self.exporter.send_export(export=export, params={})
        params = mock_launch.call_args.kwargs["params"]
        tables_sent = [t["tableName"] for t in params["tablesToExport"]]
        self.assertEqual(tables_sent.count("patient__identifier"), 1)
        self.assertEqual(len(params["filters"]), 1)

    def test_send_export_tolerates_lowercase_patient_table(self):
        # Ref #3289: the AdministrationPortal used to send `table_name: 'patient'` (lowercase) while the
        # required table is "Patient". The lookup is case-insensitive so the export still reaches the
        # data-exporter, and the canonical "Patient" table name is forwarded regardless of stored casing.
        export = self._build_datalab_export(patient_table_name="patient")
        with mock.patch.object(self.exporter.export_api, "launch_export", return_value="job-id") as mock_launch:
            self.exporter.send_export(export=export, params={})
        mock_launch.assert_called_once()
        tables_sent = [t["tableName"] for t in mock_launch.call_args.kwargs["params"]["tablesToExport"]]
        self.assertIn("Patient", tables_sent)
        self.assertNotIn("patient", tables_sent)
        self.assertIn("death_date_insee", tables_sent)
