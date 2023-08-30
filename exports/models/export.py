from django.db import models
from django.db.models import CASCADE

from admin_cohort.models import User
from exports.models import Datalab
from exports.models.base_model import ExportsBaseModel
from exports.types import ExportStatus, ExportType

STATUSES = [(status.name, status.value) for status in ExportStatus]
OUTPUT_FORMATS = [(status.value, status.name) for status in ExportType]


class Export(ExportsBaseModel):
    name = models.CharField(null=False, max_length=255)
    motivation = models.TextField(null=True)
    create_datetime = models.DateTimeField(auto_now=True)
    clean_datetime = models.DateTimeField()
    status = models.CharField(choices=STATUSES)
    datalab = models.ForeignKey(to=Datalab, related_name="exports", on_delete=CASCADE)
    owner = models.ForeignKey(to=User, related_name="exports", on_delete=CASCADE)
    output_format = models.CharField(null=True, choices=OUTPUT_FORMATS)
    target_name = models.CharField(null=True)
    target_location = models.TextField(null=True)
    data_exporter_version = models.CharField(null=True)
    data_version = models.CharField(null=True)
    nominative = models.BooleanField(null=False)
    shift_dates = models.BooleanField(null=False)
    is_user_notified = models.BooleanField(null=False)

    class Meta:
        db_table = 'export'
