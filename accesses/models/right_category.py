from django.db import models

from admin_cohort.models import BaseModel


class RightCategory(BaseModel):
    id = models.AutoField(primary_key=True)
    name = models.CharField(blank=False, null=False)
    is_global = models.BooleanField(default=False, null=False)
