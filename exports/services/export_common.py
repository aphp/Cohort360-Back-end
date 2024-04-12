from typing import List

from requests import Response

from admin_cohort.models import User
from exports.models import ExportRequest, Export
from exports.services.export_operators import ExportDownloader, ExportManager
from exports.tasks import launch_export_task


class ExportBaseService:

    @staticmethod
    def validate_export_data(data: dict, owner: User) -> None:
        ExportManager().validate(export_data=data, owner=owner)

    def proceed_with_export(self, export: ExportRequest | Export, tables: List[dict], **kwargs) -> None:
        requires_cohort_subsets = self.create_tables(export, tables, **kwargs)
        if not requires_cohort_subsets:
            launch_export_task.delay(export.pk, Export)

    @staticmethod
    def create_tables(export: ExportRequest | Export, tables: List[dict], **kwargs) -> bool:
        raise NotImplementedError("Implement in subclass depending on `type(export)")

    @staticmethod
    def download(export: ExportRequest | Export) -> Response:
        return ExportDownloader().download(export=export)
