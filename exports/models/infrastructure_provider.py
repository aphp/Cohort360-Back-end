from uuid import uuid4

from django.db import models


class InfrastructureProvider(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid4, editable=False, auto_created=True)
    name = models.CharField(null=False)

    class Meta:
        db_table = 'infrastructure_provider'
