from uuid import uuid4

from django.db import models
from django.db.models import CASCADE

from admin_cohort.models import User
from exports.models import Datalab

STATUSES = [("pending", "En Attente"),
            ("sent_to_de", "Envoyé au DE"),
            ("delivered", "Livré")]

OUTPUT_FORMATS = [("csv", "CSV"),
                  ("hive", "HIVE")]


class Export(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid4, editable=False, auto_created=True)
    name = models.CharField(null=False, max_length=255)
    motivation = models.TextField(null=True)
    create_datetime = models.DateTimeField(auto_now=True)
    clean_datetime = models.DateTimeField()
    status = models.CharField(choices=STATUSES)
    datalab = models.ForeignKey(Datalab, related_name="exports", on_delete=CASCADE)
    owner = models.ForeignKey(User, related_name="exports", on_delete=CASCADE)
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
