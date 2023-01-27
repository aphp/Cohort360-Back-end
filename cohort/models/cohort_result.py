from __future__ import annotations

from django.db import models

from admin_cohort.models import CohortBaseModel, JobModel, User
from admin_cohort.settings import COHORT_LIMIT
from cohort.models import COHORT_TYPE_CHOICES, MY_COHORTS_COHORT_TYPE
from cohort.models.dated_measure import DatedMeasure
from cohort.models.request_query_snapshot import RequestQuerySnapshot


class CohortResult(CohortBaseModel, JobModel):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_cohorts')
    name = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    favorite = models.BooleanField(default=False)
    request_query_snapshot = models.ForeignKey(RequestQuerySnapshot, on_delete=models.CASCADE,
                                               related_name='cohort_results')
    fhir_group_id = models.CharField(max_length=64, blank=True)
    dated_measure = models.ForeignKey(DatedMeasure, related_name="cohort", on_delete=models.CASCADE)
    dated_measure_global = models.ForeignKey(DatedMeasure, related_name="restricted_cohort", null=True,
                                             on_delete=models.SET_NULL)
    create_task_id = models.TextField(blank=True)
    type = models.CharField(max_length=20, choices=COHORT_TYPE_CHOICES, default=MY_COHORTS_COHORT_TYPE)

    @property
    def result_size(self):
        return self.dated_measure.measure

    @property
    def exportable(self):
        return self.result_size < COHORT_LIMIT
