from enum import StrEnum

from django.db import models
from django.utils import timezone

from admin_cohort.models import BaseModel


class MaintenanceType(StrEnum):
    PARTIAL = 'partial'
    FULL = 'full'


MAINTENANCE_TYPE_CHOICES = [
    (MaintenanceType.PARTIAL, 'Partial'),
    (MaintenanceType.FULL, 'Full'),
]


class MaintenancePhase(BaseModel):
    id = models.AutoField(primary_key=True)
    subject = models.TextField()
    message = models.TextField(null=True)
    type = models.CharField(max_length=10, choices=MAINTENANCE_TYPE_CHOICES, default=MaintenanceType.PARTIAL)
    start_datetime = models.DateTimeField(null=False)
    end_datetime = models.DateTimeField(null=False)

    @property
    def active(self):
        return self.start_datetime < timezone.now() < self.end_datetime

