from __future__ import annotations

from django.db import models

from admin_cohort.models import CohortBaseModel, User


class Folder(CohortBaseModel):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='folders')
    name = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.name} ({self.owner})"

    def __repr__(self):
        return f"Folder {self})"
