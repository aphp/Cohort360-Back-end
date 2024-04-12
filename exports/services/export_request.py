from typing import List

from exports.models import ExportRequest, ExportRequestTable
from exports.services.export_common import ExportBaseService


class ExportRequestService(ExportBaseService):

    @staticmethod
    def create_tables(export: ExportRequest, tables: List[dict], **kwargs) -> bool:
        for table in tables:
            ExportRequestTable.objects.create(export_request=export, **table)
        return False


export_request_service = ExportRequestService()
