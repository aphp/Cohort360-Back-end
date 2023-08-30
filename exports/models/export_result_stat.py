from django.db import models
from django.db.models import CASCADE

from exports.models import ExportsBaseModel, Export
from exports.types import StatType

STAT_TYPES = [(type.name, type.value) for type in StatType]


class ExportResultStat(ExportsBaseModel):
    export = models.ForeignKey(to=Export, related_name="stats", on_delete=CASCADE)
    name = models.CharField(null=False, max_length=55)
    type = models.CharField(null=False, choices=STAT_TYPES, max_length=20)
    value = models.CharField(null=False, max_length=55)

    class Meta:
        db_table = 'export_result_stat'
