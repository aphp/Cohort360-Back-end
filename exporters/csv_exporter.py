import os
from typing import List

from django.db.models import Q

from admin_cohort.models import User
from cohort.models import CohortResult
from exports.models import ExportRequest, Export
from exporters.base_exporter import BaseExporter
from exporters.enums import ExportTypes


class CSVExporter(BaseExporter):

    def __init__(self):
        super().__init__()
        self.type = ExportTypes.CSV.value
        self.target_location = os.environ.get('EXPORT_CSV_PATH')

    def get_source_cohorts(self, export_data: dict, **kwargs) -> List[str]:
        source_cohorts_ids = []
        using_new_export_models = self.using_new_export_models(export_data=export_data)
        if not using_new_export_models:
            q = Q(fhir_group_id=export_data['cohort_id'])
        else:
            source_cohorts_ids = [t.get("cohort_result_source") for t in export_data.get("export_tables", [])]
            assert len(set(source_cohorts_ids)) == 1, "All export tables must have the same source cohort"
            q = Q(pk=source_cohorts_ids[0])

        try:
            cohort = CohortResult.objects.get(q & Q(owner=kwargs.get("owner")))
        except (CohortResult.DoesNotExist, CohortResult.MultipleObjectsReturned) as e:
            raise ValueError(f"Missing cohort with id {q.children[0][1]} - {e}")

        if not using_new_export_models:
            export_data['cohort'] = cohort.uuid
            source_cohorts_ids = [cohort.uuid]
        return source_cohorts_ids

    def validate(self, export_data: dict, **kwargs) -> None:
        source_cohorts_ids = self.get_source_cohorts(export_data=export_data, owner=kwargs.get("owner"))
        if not export_data.get('nominative', False):
            raise ValueError("CSV exports must be in `nominative` mode")
        kwargs["source_cohorts_ids"] = source_cohorts_ids
        super().validate(export_data=export_data, **kwargs)

    def complete_data(self, export_data: dict, owner: User, **kwargs) -> None:
        kwargs["target_name"] = owner.pk
        super().complete_data(export_data=export_data, owner=owner, **kwargs)

    def handle_export(self, export: ExportRequest | Export, **kwargs) -> None:
        self.confirm_export_received(export=export)
        kwargs["params"] = {"file_path": f"{export.target_full_path}.zip"}
        super().handle_export(export=export, **kwargs)