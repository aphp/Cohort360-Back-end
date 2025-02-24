from __future__ import annotations

from django.db import models

from admin_cohort.models import JobModel, User
from cohort.models import CohortBaseModel, RequestQuerySnapshot, DatedMeasure

COHORT_TYPES = [("IMPORT_I2B2", "Previous cohorts imported from i2b2."),
                ("MY_ORGANIZATIONS", "Organizations in which I work (care sites with pseudo-anonymised reading rights)."),
                ("MY_PATIENTS", "Patients that passed by all my organizations (care sites with nominative reading rights)."),
                ("MY_COHORTS", "Cohorts I created in Cohort360")]

MY_COHORTS_TYPE = COHORT_TYPES[3][0]


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
    type = models.CharField(max_length=20, choices=COHORT_TYPES, default=MY_COHORTS_TYPE)
    is_subset = models.BooleanField(default=False)
    parent_cohort = models.ForeignKey("CohortResult", related_name="sample_cohorts", on_delete=models.SET_NULL, null=True)
    sampling_ratio = models.FloatField(blank=True, null=True)
