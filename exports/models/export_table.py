from uuid import uuid4

from django.db import models
from django.db.models import CASCADE

from cohort.models import FhirFilter
from exports.models import Export


class ExportTable(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid4, editable=False, auto_created=True)
    name = models.CharField(null=False)
    export = models.ForeignKey(Export, related_name="tables", on_delete=CASCADE)
    respect_table_relationships = models.BooleanField(null=False, default=True)
    filter = models.ForeignKey(FhirFilter, related_name="export_tables", null=True, on_delete=CASCADE)
    cohort_definition_subset = models.ForeignKey(CohortDefinitionSubset, related_name="export_tables", null=True, on_delete=CASCADE)

    class Meta:
        db_table = 'export_table'
