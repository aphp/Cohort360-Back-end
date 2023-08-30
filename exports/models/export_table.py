from django.db import models
from django.db.models import CASCADE

from cohort.models import FhirFilter, CohortResult
from exports.models import Export
from exports.models.base_model import ExportsBaseModel


class ExportTable(ExportsBaseModel):
    name = models.CharField(null=False)
    export = models.ForeignKey(to=Export, related_name="tables", on_delete=CASCADE)
    respect_table_relationships = models.BooleanField(null=False, default=True)
    filter = models.ForeignKey(to=FhirFilter, related_name="export_tables", null=True, on_delete=CASCADE)
    cohort_result_subset = models.ForeignKey(to=CohortResult, related_name="export_tables", null=True, on_delete=CASCADE)

    class Meta:
        db_table = 'export_table'
