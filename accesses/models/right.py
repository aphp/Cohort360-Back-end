from django.db import models

from accesses.models import RightCategory
from admin_cohort.models import BaseModel


class Right(BaseModel):
    id = models.AutoField(primary_key=True)
    name = models.CharField(blank=False, null=False)
    label = models.CharField(blank=False, null=False)
    depends_on = models.ForeignKey("Right", related_name="dependent_rights", on_delete=models.SET_NULL, null=True)
    category = models.ForeignKey(RightCategory, related_name="rights", on_delete=models.SET_NULL, null=True)
    allow_read_accesses_on_same_level = models.BooleanField(null=True, default=False)
    allow_read_accesses_on_inf_levels = models.BooleanField(null=True, default=False)
    allow_edit_accesses_on_same_level = models.BooleanField(null=True, default=False)
    allow_edit_accesses_on_inf_levels = models.BooleanField(null=True, default=False)
    impact_inferior_levels = models.BooleanField(null=True, default=False)


all_rights = Right.objects.all()
