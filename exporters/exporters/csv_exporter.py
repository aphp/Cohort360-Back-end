import os

from django.db.models import Q

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

    def validate(self, export_data: dict, **kwargs) -> None:
        if not export_data.get('nominative', False):
            raise ValueError("Export must be in `nominative` mode")
        source_cohort_id = export_data.get("cohort_result_source")
        if not CohortResult.objects.filter(Q(pk=source_cohort_id) &
                                           Q(owner=kwargs.get("owner")))\
                                   .exists():
            raise ValueError(f"Missing cohort with ID {source_cohort_id}")
        kwargs["source_cohorts_ids"] = [source_cohort_id]
        super().validate(export_data=export_data, **kwargs)

    def complete_data(self, export_data: dict, owner: User, **kwargs) -> None:
        kwargs["target_name"] = owner.pk
        super().complete_data(export_data=export_data, owner=owner, **kwargs)

    def handle_export(self, export: Export, params: dict = None) -> None:
        self.confirm_export_received(export=export)
        params = {"export_in_one_table": export.group_tables,
                  "file_path": f"{export.target_full_path}.zip"
                  }
        super().handle_export(export=export, params=params)
