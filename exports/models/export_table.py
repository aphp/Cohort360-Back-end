from django.db import models
from django.db.models import CASCADE

from cohort.models import FhirFilter, CohortResult
from exports.models import ExportsBaseModel, Export


class ExportTable(ExportsBaseModel):
    name = models.CharField(null=False, max_length=55)
    export = models.ForeignKey(to=Export, related_name="export_tables", on_delete=CASCADE)
    respect_table_relationships = models.BooleanField(null=False, default=True)
    fhir_filter = models.ForeignKey(to=FhirFilter, related_name="export_tables", null=True, on_delete=CASCADE)
    cohort_result_subset = models.ForeignKey(to=CohortResult, related_name="export_tables", null=True, on_delete=CASCADE)

    class Meta:
        db_table = 'export_table'
