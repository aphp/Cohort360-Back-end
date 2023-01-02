from django.db import models
from django.db.models import CASCADE

from exports.models import ExportRequest


class ExportRequestTable(models.Model):
    export_request_table_id = models.BigAutoField(primary_key=True)
    omop_table_name = models.TextField()
    source_table_name = models.TextField(null=True)
    export_request = models.ForeignKey(ExportRequest, related_name="tables", on_delete=CASCADE)

    class Meta:
        db_table = 'export_request_table'
