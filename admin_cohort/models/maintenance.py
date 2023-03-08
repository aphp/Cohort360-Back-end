from typing import Union

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


def get_next_maintenance() -> Union[MaintenancePhase, None]:
    now = timezone.now()
    current = MaintenancePhase.objects.filter(start_datetime__lte=now, end_datetime__gte=now)\
                                      .order_by('-end_datetime')\
                                      .first()
    if current:
        return current
    next_maintenance = MaintenancePhase.objects.filter(start_datetime__gte=timezone.now())\
                                               .order_by('start_datetime')\
                                               .first()
    return next_maintenance
