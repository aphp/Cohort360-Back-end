from django.db import models
from django.db.models import UniqueConstraint, Q

from cohort.models import CohortBaseModel, Request
from cohort.services.utils import RefreshFrequency


REFRESH_FREQUENCIES = [(rf.value, rf.value) for rf in RefreshFrequency]


class RequestRefreshSchedule(CohortBaseModel):
    request = models.ForeignKey(Request, on_delete=models.CASCADE, related_name='refresh_schedules')
    refresh_time = models.TimeField()
    refresh_frequency = models.CharField(choices=REFRESH_FREQUENCIES)
    last_refresh = models.DateTimeField()
    last_refresh_success = models.BooleanField()
    last_refresh_count = models.CharField()
    last_refresh_error_msg = models.CharField()
    notify_owner = models.BooleanField(default=False)

    class Meta:
        constraints = [UniqueConstraint(name='unique_request_refresh_schedule',
                                        fields=['request'],
                                        condition=Q(deleted__isnull=True))]
