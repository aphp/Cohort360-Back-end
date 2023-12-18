from django.db import models

from admin_cohort.models import User
from cohort.models import CohortBaseModel, DatedMeasure


class FeasibilityResult(CohortBaseModel):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='feasibility_results')
    total_count = models.IntegerField(null=False, blank=False)
    dated_measure = models.OneToOneField(DatedMeasure, related_name="feasibility_result", on_delete=models.CASCADE, null=False)
    # todo: get `eligibility_criteria` from dm.RQS.serialized_query
    # eligibility_criteria = models.CharField(...)


class FeasibilityResultCount(CohortBaseModel):
    perimeter_id = models.IntegerField(null=False, blank=False)
    count = models.IntegerField(null=False, blank=False)
    feasibility_result = models.ForeignKey(FeasibilityResult, related_name="feasibility_result_counts", on_delete=models.CASCADE, null=False)
