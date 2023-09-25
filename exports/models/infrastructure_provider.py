from django.db import models

from exports.models import ExportsBaseModel


class InfrastructureProvider(ExportsBaseModel):
    name = models.CharField(null=False, max_length=255)

    class Meta:
        db_table = 'infrastructure_provider'
