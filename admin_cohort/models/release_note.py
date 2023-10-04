from django.contrib.postgres.fields import ArrayField
from django.db import models

from admin_cohort.models import BaseModel


class ReleaseNote(BaseModel):
    id = models.AutoField(primary_key=True)
    title = models.TextField()
    message = ArrayField(base_field=models.TextField(), null=False, blank=True)
    author = models.TextField(null=True)

    class Meta:
        db_table = 'release_note'
