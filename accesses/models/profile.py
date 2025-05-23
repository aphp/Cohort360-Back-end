from __future__ import annotations

from django.db import models
from django.db.models import CASCADE
from django.conf import settings

from admin_cohort.models import BaseModel, User

MANUAL = settings.ACCESS_SOURCES[0]


class Profile(BaseModel):
    id = models.AutoField(blank=True, null=False, primary_key=True)
    source = models.TextField(blank=True, null=True, default=MANUAL)
    is_active = models.BooleanField(blank=True, null=True)
    user = models.ForeignKey(User, on_delete=CASCADE, related_name='profiles', null=True, blank=True)
