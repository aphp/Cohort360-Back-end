from django.db import models


class JupyterMachine(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=60, null=False)
