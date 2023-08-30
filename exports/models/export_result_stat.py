from django.db import models
from django.db.models import CASCADE

from exports.models import Export
from exports.models.base_model import ExportsBaseModel

STAT_TYPES = [("int", "Integer"),
              ("txt", "Text"),
              ("size_bytes", "Size Bytes")]


class ExportResultStat(ExportsBaseModel):
    export = models.ForeignKey(to=Export, related_name="tables", on_delete=CASCADE)
    name = models.CharField(null=False)
    type = models.CharField(null=False, choices=STAT_TYPES)
    value = models.CharField(null=False)

    class Meta:
        db_table = 'export_result_stat'
