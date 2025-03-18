from __future__ import annotations

from datetime import timedelta

from django.db import models
from django.utils import timezone
from django.conf import settings

from admin_cohort.models import JobModel, User
from cohort.models import CohortBaseModel, RequestQuerySnapshot

SNAPSHOT_DM_MODE = "Snapshot"
GLOBAL_DM_MODE = "Global"
DATED_MEASURE_MODE_CHOICES = [(SNAPSHOT_DM_MODE, SNAPSHOT_DM_MODE),
                              (GLOBAL_DM_MODE, GLOBAL_DM_MODE)]


class DatedMeasure(CohortBaseModel, JobModel):
    # todo : fix this, user_request_query_results is wrong
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_request_query_results')
    request_query_snapshot = models.ForeignKey(RequestQuerySnapshot, on_delete=models.CASCADE, related_name='dated_measures')
    fhir_datetime = models.DateTimeField(null=True, blank=False)
    measure = models.BigIntegerField(null=True, blank=False)
    measure_min = models.BigIntegerField(null=True, blank=False)
    measure_max = models.BigIntegerField(null=True, blank=False)
    extra = models.JSONField(null=True, blank=True)
    count_task_id = models.TextField(blank=True)
    mode = models.CharField(max_length=20, choices=DATED_MEASURE_MODE_CHOICES, default=SNAPSHOT_DM_MODE, null=True)

    @property
    def count_outdated(self) -> bool:
        delta = timedelta(hours=settings.LAST_COUNT_VALIDITY)
        return timezone.now() - self.created_at > delta

    @property
    def cohort_limit(self) -> int:
        return settings.COHORT_LIMIT

    @property
    def is_global(self) -> bool:
        return self.mode == GLOBAL_DM_MODE
