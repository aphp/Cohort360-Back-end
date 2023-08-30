from django.db import models
from django.db.models import CASCADE

from exports.models import InfrastructureProvider
from exports.models.base_model import ExportsBaseModel


class Datalab(ExportsBaseModel):
    infrastructure_provider = models.ForeignKey(to=InfrastructureProvider, related_name="exports", null=True, on_delete=CASCADE)

    class Meta:
        db_table = 'datalab'
