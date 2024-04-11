from typing import List

from requests import Response

from admin_cohort.models import User
from exports.models import ExportRequest, ExportRequestTable
from exports.services.export_operators import ExportDownloader, ExportManager
from exports.tasks import launch_export_task


class ExportRequestService:

    @staticmethod
    def validate_export_data(data: dict, owner: User) -> None:
        ExportManager().validate(export_data=data, owner=owner)

    def proceed_with_export(self, export: ExportRequest, tables: List[dict]) -> None:
        self.create_tables(export, tables)
        launch_export_task.delay(export.id, ExportRequest)

    @staticmethod
    def create_tables(export_request: ExportRequest, tables: List[dict]) -> None:
        for table in tables:
            ExportRequestTable.objects.create(export_request=export_request, **table)

    @staticmethod
    def download(export) -> Response:
        return ExportDownloader().download(export=export)


export_request_service = ExportRequestService()
