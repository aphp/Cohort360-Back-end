from django.db import models
from django.db.models import DO_NOTHING

from exports.models import ExportsBaseModel, InfrastructureProvider


class Datalab(ExportsBaseModel):
    infrastructure_provider = models.ForeignKey(to=InfrastructureProvider, related_name="datalabs", on_delete=DO_NOTHING)

    class Meta:
        db_table = 'datalab'
