from django.db import models
from django.db.models import CASCADE

from admin_cohort.models import User
from exports.models import ExportsBaseModel, Datalab
from exports.types import ExportStatus, ExportType

STATUSES = [(status.name, status.value) for status in ExportStatus]
OUTPUT_FORMATS = [(out_format.value, out_format.value) for out_format in ExportType]


class Export(ExportsBaseModel):
    name = models.CharField(null=False, max_length=255)
    motivation = models.TextField(null=True)
    clean_datetime = models.DateTimeField(null=True)
    status = models.CharField(choices=STATUSES, max_length=55, null=True)
    datalab = models.ForeignKey(to=Datalab, related_name="exports", on_delete=CASCADE, null=True)
    owner = models.ForeignKey(to=User, related_name="exports", on_delete=CASCADE)
    output_format = models.CharField(null=False, choices=OUTPUT_FORMATS, max_length=20)
    target_name = models.CharField(null=True, max_length=255)
    target_location = models.TextField(null=True)
    data_exporter_version = models.CharField(null=True, max_length=20)
    data_version = models.CharField(null=True, max_length=20)
    nominative = models.BooleanField(null=False, default=False)
    shift_dates = models.BooleanField(null=False, default=False)
    is_user_notified = models.BooleanField(null=False, default=False)

    class Meta:
        db_table = 'export'

    @property
    def target_full_path(self) -> str:
        if self.target_location and self.target_name:
            extensions = {ExportType.CSV.value: ".zip",
                          ExportType.HIVE.value: ".db"
                          }
            return f"{self.target_location}/{self.target_name}{extensions.get(self.output_format)}"
        return ""

    @property
    def target_datalab(self) -> str:
        return self.datalab and self.datalab.name or ""
