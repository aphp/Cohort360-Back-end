import os

from django.db.models import Q
from rest_framework.exceptions import ValidationError

from admin_cohort.models import User
from cohort.models import CohortResult
from exports.models import ExportRequest, Export
from exporters.base_exporter import BaseExporter
from exporters.enums import ExportTypes
from exporters.tasks import notify_export_received


class CSVExporter(BaseExporter):

    def __init__(self):
        super().__init__()
        self.type = ExportTypes.CSV
        self.target_location = os.environ.get('EXPORT_CSV_PATH')

    def validate(self, export_data: dict, owner: User, **kwargs) -> None:
        source_cohorts_ids = []
        using_new_export_models = self.using_new_export_models(export_data=export_data)
        if using_new_export_models:
            source_cohorts_ids = [t.get("cohort_result_source") for t in export_data.get("export_tables", [])]
            assert len(set(source_cohorts_ids)) == 1, "All export tables must have the same source cohort"
            q = Q(pk__in=source_cohorts_ids)
        else:
            q = Q(fhir_group_id=export_data['cohort_id'])

        try:
            cohort = CohortResult.objects.get(q)
        except (CohortResult.DoesNotExist, CohortResult.MultipleObjectsReturned) as e:
            raise ValidationError(f"Missing cohort with id {q.children[0][1]} - {e}")

        if not using_new_export_models:
            export_data['cohort'] = cohort.uuid
            source_cohorts_ids = [cohort.uuid]

        if cohort.owner != owner:
            raise ValueError("The selected cohort does not belong to you")
        if not export_data.get('nominative', False):
            raise ValidationError("CSV exports must be in `nominative` mode")
        super().validate(export_data=export_data, owner=owner, source_cohorts_ids=source_cohorts_ids)

    def complete_data(self, export_data: dict, owner: User, **kwargs) -> None:
        kwargs["target_name"] = owner.pk
        super().complete_data(export_data=export_data, owner=owner, **kwargs)

    def handle_export(self, export: ExportRequest | Export) -> None:
        notify_export_received.delay(export.pk)
        super().handle(export=export, params={"file_path": f"{export.target_full_path}.zip"})
