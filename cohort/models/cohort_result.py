from __future__ import annotations

from django.db import models
from django.conf import settings

from admin_cohort.models import JobModel, User
from cohort.models import CohortBaseModel, RequestQuerySnapshot, DatedMeasure


class CohortResult(CohortBaseModel, JobModel):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_cohorts')
    name = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    favorite = models.BooleanField(default=False)
    request_query_snapshot = models.ForeignKey(RequestQuerySnapshot, on_delete=models.CASCADE, related_name='cohort_results', null=True)
    group_id = models.CharField(max_length=64, blank=True)
    dated_measure = models.ForeignKey(DatedMeasure, related_name="cohorts", on_delete=models.CASCADE, null=True)
    dated_measure_global = models.ForeignKey(DatedMeasure, related_name="global_cohorts", null=True, on_delete=models.SET_NULL)
    create_task_id = models.TextField(blank=True)
    is_subset = models.BooleanField(default=False)

    @property
    def result_size(self) -> int:
        return self.dated_measure.measure

    @property
    def measure_min(self) -> int:
        return self.dated_measure_global and self.dated_measure_global.measure_min

    @property
    def measure_max(self) -> int:
        return self.dated_measure_global and self.dated_measure_global.measure_max

    @property
    def exportable(self) -> bool:
        cohort_size = self.result_size
        return cohort_size and cohort_size < settings.COHORT_LIMIT or False
