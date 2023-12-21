from __future__ import annotations

from django.db import models

from admin_cohort.models import User, JobModel
from cohort.models import RequestQuerySnapshot, CohortBaseModel


class FeasibilityStudy(CohortBaseModel, JobModel):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='feasibility_studies')
    request_query_snapshot = models.ForeignKey(RequestQuerySnapshot, on_delete=models.CASCADE, related_name='feasibility_studies')
    total_count = models.IntegerField()
    display_eligibility_criteria = models.BooleanField(default=False)
    display_total_count = models.BooleanField(default=False)
    display_count_by_ghu = models.BooleanField(default=False)
    display_count_by_hospital = models.BooleanField(default=False)
    display_count_by_uf = models.BooleanField(default=False)
    display_visit_dates = models.BooleanField(default=False)
    display_demographic_info = models.BooleanField(default=False)
    display_repartition_graphs = models.BooleanField(default=False)
    display_visit_graph = models.BooleanField(default=False)
    display_demographic_graph = models.BooleanField(default=False)
    report_json_content = models.BinaryField(null=True, blank=True)
    report_file = models.BinaryField(null=True, blank=True)
