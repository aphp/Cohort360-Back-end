from django.db import models

from accesses.models import RightCategory
from admin_cohort.models import BaseModel


class Right(BaseModel):
    id = models.AutoField(primary_key=True)
    name = models.CharField(blank=False, null=False)
    label = models.CharField(blank=False, null=False)
    depends_on = models.ForeignKey("Right", related_name="dependent_rights", on_delete=models.SET_NULL, null=True)
    category = models.ForeignKey(RightCategory, related_name="rights", on_delete=models.SET_NULL, null=True)
