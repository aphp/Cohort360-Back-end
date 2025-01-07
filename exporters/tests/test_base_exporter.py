from unittest import mock

from exporters.exporters.base_exporter import BaseExporter
from exporters.enums import ExportTypes
from exporters.tests.base_test import ExportersTestBase


class TestBaseExporter(ExportersTestBase):

    def setUp(self) -> None:
        super().setUp()
        self.api_conf = {
            "INFRA_API": {
                "API_URL": 'https://infra-api.fr/api',
                "AUTH_TOKEN": "hadoop-token",
                "TASK_STATUS_ENDPOINT": '/hadoop/task_status',
                "CREATE_DB_ENDPOINT": '/hadoop/create_db',
                "ALTER_DB_ENDPOINT": '/hadoop/chown_db',
            },
            "EXPORT_API": {
                "API_URL": 'https://export-api.fr/api',
                "AUTH_TOKEN": "bigdata-token",
                "TASK_STATUS_ENDPOINT": '/task_status',
            },
        }
        with mock.patch('exporters.apis.base.ExportersConfig') as mock_exports_config:
            mock_exports_config.THIRD_PARTY_API_CONF = self.api_conf
            self.exporter = BaseExporter()

    def test_complete_export_data(self):
        export_data = dict(output_format=ExportTypes.HIVE.value,
                           datalab=self.datalab.pk,
                           nominative=True,
                           motivation='motivation\nover\nmultiple\nlines',
                           export_tables=[{"table_name": "table1",
                                           "cohort_result_source": self.cohort.uuid
                                           }]
                           )
        self.exporter.complete_data(export_data=export_data, owner=self.csv_exporter_user)
        self.assertIn("owner", export_data)
        self.assertIn("target_name", export_data)
        self.assertIn("target_location", export_data)
        self.assertNotIn("\n", export_data["motivation"])
