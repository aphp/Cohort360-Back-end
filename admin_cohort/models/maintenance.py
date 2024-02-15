from django.db import models
from django.utils import timezone

from admin_cohort.models import BaseModel


class MaintenancePhase(BaseModel):
    id = models.AutoField(primary_key=True)
    subject = models.TextField()
    start_datetime = models.DateTimeField(null=False)
    end_datetime = models.DateTimeField(null=False)

    @property
    def active(self):
        return self.start_datetime < timezone.now() < self.end_datetime
