from datetime import timedelta
from typing import Optional

from django.db import models
from django.db.models import CASCADE
from django.conf import settings
from django.utils import timezone

from admin_cohort.models import User, JobModel
from exports.models import ExportsBaseModel, Datalab
from exports.apps import ExportsConfig

OUTPUT_FORMATS = [(t.value, t.value) for t in ExportsConfig.ExportTypes]


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

    def available_for_download(self) -> bool:
        return self.created_at + timedelta(days=settings.DAYS_TO_KEEP_EXPORTED_FILES) > timezone.now()
