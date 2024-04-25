from typing import List

from django.http import StreamingHttpResponse
from rest_framework.exceptions import ValidationError

from exports.models import ExportRequest, Export
from exports.services.export_operators import ExportDownloader, ExportManager
from exports.tasks import launch_export_task


class ExportBaseService:

    @staticmethod
    def validate_export_data(data: dict, **kwargs) -> None:
        try:
            ExportManager().validate(export_data=data, **kwargs)
        except Exception as e:
            raise ValidationError(f'Invalid export data: {e}')

    def proceed_with_export(self, export: ExportRequest | Export, tables: List[dict], **kwargs) -> None:
        requires_cohort_subsets = self.create_tables(export, tables, **kwargs)
        if not requires_cohort_subsets:
            launch_export_task.delay(export.pk)

    @staticmethod
    def create_tables(export: ExportRequest | Export, tables: List[dict], **kwargs) -> bool:
        raise NotImplementedError("Implement in subclass depending on export model")

    @staticmethod
    def download(export: ExportRequest | Export) -> StreamingHttpResponse:
        return ExportDownloader().download(export=export)
