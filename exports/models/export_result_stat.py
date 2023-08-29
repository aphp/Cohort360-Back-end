from uuid import uuid4

from django.db import models
from django.db.models import CASCADE

from exports.models import Export

STAT_TYPES = [("int", "Integer"),
              ("txt", "Text"),
              ("size_bytes", "Size Bytes")]


class ExportResultStat(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid4, editable=False, auto_created=True)
    export = models.ForeignKey(Export, related_name="tables", on_delete=CASCADE)
    name = models.CharField(null=False)
    type = models.CharField(null=False, choices=STAT_TYPES)
    value = models.CharField(null=False)

    class Meta:
        db_table = 'export_result_stat'
