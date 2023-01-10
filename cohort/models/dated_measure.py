from __future__ import annotations

from django.db import models

from admin_cohort.models import CohortBaseModel, JobModel, User
from . import RequestQuerySnapshot, DATED_MEASURE_MODE_CHOICES, SNAPSHOT_DM_MODE


class DatedMeasure(CohortBaseModel, JobModel):
    """
    This is an intermediary result giving only limited info before
    possibly generating a Cohort/Group in Fhir.
    """
    # todo : fix this, user_request_query_results is wrong
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_request_query_results')
    request_query_snapshot = models.ForeignKey(RequestQuerySnapshot, on_delete=models.CASCADE,
                                               related_name='dated_measures')
    fhir_datetime = models.DateTimeField(null=True, blank=False)
    # Size of potential cohort as returned by SolR
    measure = models.BigIntegerField(null=True, blank=False)
    measure_min = models.BigIntegerField(null=True, blank=False)
    measure_max = models.BigIntegerField(null=True, blank=False)
    measure_male = models.BigIntegerField(null=True, blank=True)
    measure_unknown = models.BigIntegerField(null=True, blank=True)
    measure_deceased = models.BigIntegerField(null=True, blank=True)
    measure_alive = models.BigIntegerField(null=True, blank=True)
    measure_female = models.BigIntegerField(null=True, blank=True)
    count_task_id = models.TextField(blank=True)
    mode = models.CharField(max_length=20, choices=DATED_MEASURE_MODE_CHOICES, default=SNAPSHOT_DM_MODE, null=True)
