import os

from rest_framework.exceptions import ValidationError

from admin_cohort.models import User
from cohort.models import CohortResult
from exports.models import ExportRequest, Export
from exports.enums import ExportType
from exports.exporters.base_exporter import BaseExporter


class CSVExporter(BaseExporter):

    def __init__(self):
        super().__init__()
        self.type = ExportType.CSV
        self.filepath = os.environ.get('EXPORT_CSV_PATH')

    def validate(self, export_data: dict, owner: User, **kwargs) -> None:
        try:
            cohort = CohortResult.objects.get(fhir_group_id=export_data['cohort_id'])
            export_data['cohort'] = cohort.uuid
        except (CohortResult.DoesNotExist, CohortResult.MultipleObjectsReturned) as e:
            raise ValidationError(f"Missing cohort with id {export_data['cohort_id']} - {e}")

        if cohort.owner != owner:
            raise ValidationError("The selected cohort does not belong to you")
        if not export_data.get("nominative", False):
            raise ValidationError("CSV exports must be in `nominative` mode")
        super().validate(export_data=export_data, owner=owner, cohort_id=cohort.uuid)
        self.complete_data(export_data=export_data,
                           owner=owner,
                           target_name=owner.pk,
                           target_location=self.filepath)

    def handle_export(self, export: ExportRequest | Export) -> None:
        super().handle(export=export, params={"file_path": export.target_full_path})
