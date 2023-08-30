from django.db import models

from exports.models.base_model import ExportsBaseModel


class InfrastructureProvider(ExportsBaseModel):
    name = models.CharField(null=False)

    class Meta:
        db_table = 'infrastructure_provider'
