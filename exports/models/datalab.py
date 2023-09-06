from django.db import models
from django.db.models import SET_NULL

from exports.models import ExportsBaseModel, InfrastructureProvider


class Datalab(ExportsBaseModel):
    infrastructure_provider = models.ForeignKey(to=InfrastructureProvider, related_name="datalabs", null=True, on_delete=SET_NULL)

    class Meta:
        db_table = 'datalab'
