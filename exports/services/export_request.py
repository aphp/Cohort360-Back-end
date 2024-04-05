from typing import List

from requests import Response

from admin_cohort.models import User
from exports.models import ExportRequest, ExportRequestTable
from exports.exporters.hive_exporter import HiveExporter
from exports.exporters.csv_exporter import CSVExporter
from exports.services.export_manager import ExportDownloader
from exports.enums import ExportType
from exports.tasks import launch_export_task, notify_export_request_received


class ExportRequestService:
    exporters = {ExportType.CSV: CSVExporter,
                 ExportType.HIVE: HiveExporter
                 }
    downloader = ExportDownloader

    def check_export_data(self, data: dict, owner: User) -> None:
        exporter = self.exporters.get(data["output_format"])
        exporter().validate(export_data=data, owner=owner)

    def proceed_with_export(self, export: ExportRequest, tables: List[dict]) -> None:
        self.create_tables(export, tables)
        notify_export_request_received.delay(export.id)
        launch_export_task.delay(export.id, ExportRequest)

    @staticmethod
    def create_tables(export_request: ExportRequest, tables: List[dict]) -> None:
        for table in tables:
            ExportRequestTable.objects.create(export_request=export_request, **table)

    def download(self, export) -> Response:
        return self.downloader().download(export=export)


export_request_service = ExportRequestService()
