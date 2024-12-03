from datetime import timedelta
from typing import Optional

from django.db import models
from django.db.models import CASCADE
from django.utils import timezone

from admin_cohort.models import User, JobModel
from admin_cohort.settings import DAYS_TO_KEEP_EXPORTED_FILES
from cohort.models import CohortResult
from exports.models import ExportsBaseModel, Datalab
from exports import ExportTypes

OUTPUT_FORMATS = [(t.value, t.value) for t in ExportTypes]


class Export(ExportsBaseModel, JobModel):
    owner = models.ForeignKey(to=User, related_name="exports", on_delete=CASCADE)
    output_format = models.CharField(null=False, choices=OUTPUT_FORMATS, max_length=20)
    target_name = models.CharField(null=True, max_length=255)
    target_location = models.TextField(null=True)
    data_exporter_version = models.CharField(null=True, max_length=20)
    data_version = models.CharField(null=True, max_length=20)
    nominative = models.BooleanField(null=False, default=False)
    is_user_notified = models.BooleanField(null=False, default=False)
    datalab = models.ForeignKey(to=Datalab, related_name="exports", on_delete=CASCADE, null=True)
    shift_dates = models.BooleanField(null=False, default=False)
    group_tables = models.BooleanField(null=False, default=False)
    motivation = models.TextField(null=True, blank=True)
    clean_datetime = models.DateTimeField(null=True)
    yaml_payload = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'export'

    @property
    def target_full_path(self) -> str:
        if self.target_location and self.target_name:
            return f"{self.target_location}/{self.target_name}"
        return ""

    @property
    def target_datalab(self) -> Optional[str]:
        return self.datalab and self.datalab.name or None

    @property
    def base_cohort(self) -> Optional[CohortResult]:
        if self.datalab:
            return None
        return self.export_tables.first().cohort_result_source

    @property
    def cohort_name(self) -> Optional[str]:
        return self.base_cohort and self.base_cohort.name or None

    @property
    def cohort_id(self) -> Optional[str]:
        return self.base_cohort and self.base_cohort.group_id or None

    @property
    def patients_count(self) -> Optional[int]:
        return self.base_cohort and self.base_cohort.dated_measure.measure or None

    def available_for_download(self) -> bool:
        return self.created_at + timedelta(days=DAYS_TO_KEEP_EXPORTED_FILES) > timezone.now()
