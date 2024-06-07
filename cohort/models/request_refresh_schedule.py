import os

from django.db import models
from django.db.models import UniqueConstraint, Q

from cohort.models import CohortBaseModel, Request

env = os.environ


class RequestRefreshSchedule(CohortBaseModel):
    request = models.ForeignKey(Request, on_delete=models.CASCADE, related_name='refresh_schedules')
    refresh_interval = models.IntegerField(default=env.get("REQUESTS_REFRESH_INTERVAL", 0))
    last_refresh = models.DateTimeField()
    notify_owner = models.BooleanField(default=False)

    class Meta:
        constraints = [UniqueConstraint(name='unique_request_refresh_schedule',
                                        fields=['request'],
                                        condition=Q(deleted__isnull=True))]
