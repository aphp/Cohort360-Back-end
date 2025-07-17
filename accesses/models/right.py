from django.db import models

from admin_cohort.models import BaseModel


class Right(BaseModel):
    id = models.AutoField(primary_key=True)
    name = models.CharField(blank=False, null=False)
    label = models.CharField(blank=False, null=False)
    depends_on = models.ForeignKey("Right", related_name="dependent_rights", on_delete=models.SET_NULL, null=True)
    category = models.CharField(blank=False, null=False)
    is_global = models.BooleanField(default=False, null=False)
    allow_edit_accesses_on_same_level = models.BooleanField(null=True, default=False)
    allow_edit_accesses_on_inf_levels = models.BooleanField(null=True, default=False)
    impact_inferior_levels = models.BooleanField(null=True, default=False)
