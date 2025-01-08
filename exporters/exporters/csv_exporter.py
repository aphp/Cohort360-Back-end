import os

from django.db.models import Q
from typing import List

from admin_cohort.models import User
from cohort.models import CohortResult
from exports.models import Export
from exporters.exporters.base_exporter import BaseExporter
from exporters.enums import ExportTypes


class CSVExporter(BaseExporter):

    def __init__(self):
        super().__init__()
        self.type = ExportTypes.CSV.value
        self.target_location = os.environ.get('EXPORT_CSV_PATH')

    @staticmethod
    def get_source_cohorts(export_data: dict, **kwargs) -> List[str]:
        source_cohorts_ids = [t.get("cohort_result_source")
                              for t in export_data.get("export_tables", []) if t.get("cohort_result_source")]
        if len(set(source_cohorts_ids)) != 1:
            raise ValueError("All export tables must have the same source cohort")
        source_cohort_id = source_cohorts_ids[0]
        if not CohortResult.objects.filter(Q(pk=source_cohort_id) &
                                           Q(owner=kwargs.get("owner"))) \
                                   .exists():
            raise ValueError(f"Missing cohort with id {source_cohort_id}")
        return source_cohorts_ids

    def validate(self, export_data: dict, **kwargs) -> None:
        if not export_data.get('nominative', False):
            raise ValueError("Export must be in `nominative` mode")
        source_cohorts_ids = self.get_source_cohorts(export_data=export_data, owner=kwargs.get("owner"))
        kwargs["source_cohorts_ids"] = source_cohorts_ids
        super().validate(export_data=export_data, **kwargs)

    def complete_data(self, export_data: dict, owner: User, **kwargs) -> None:
        kwargs["target_name"] = owner.pk
        super().complete_data(export_data=export_data, owner=owner, **kwargs)

    def handle_export(self, export: Export, params: dict = None) -> None:
        self.confirm_export_received(export=export)
        params = params or {"joinOnPrimarykey": export.group_tables,
                            "output": {"type": self.type,
                                       "filePath": f"{export.target_full_path}.zip"
                                       },
                            }
        super().handle_export(export=export, params=params)
