from django.db import models
from django.db.models import CASCADE

from exports.models import InfrastructureProvider


class Datalab(models.Model):
    id = models.AutoField(blank=True, null=False, primary_key=True)
    create_datetime = models.DateTimeField(auto_now=True)
    infrastructure_provider = models.ForeignKey(InfrastructureProvider, related_name="exports", null=True, on_delete=CASCADE)

    class Meta:
        db_table = 'datalab'
