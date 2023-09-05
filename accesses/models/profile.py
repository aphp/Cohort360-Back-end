from __future__ import annotations

from django.db import models
from django.db.models import CASCADE
from django.utils.datetime_safe import datetime

from admin_cohort.models import BaseModel, User
from admin_cohort.settings import MANUAL_SOURCE


class Profile(BaseModel):
    id = models.AutoField(blank=True, null=False, primary_key=True)
    provider_id = models.CharField(max_length=25, blank=True, null=True)
    provider_name = models.TextField(blank=True, null=True)
    firstname = models.TextField(blank=True, null=True)
    lastname = models.TextField(blank=True, null=True)
    email = models.TextField(blank=True, null=True)
    source = models.TextField(blank=True, null=True, default=MANUAL_SOURCE)
    is_active = models.BooleanField(blank=True, null=True)
    valid_start_datetime = models.DateTimeField(blank=True, null=True)
    valid_end_datetime = models.DateTimeField(blank=True, null=True)
    # fields with prefix "manual_" prime over their equivalents
    manual_is_active = models.BooleanField(blank=True, null=True)
    manual_valid_start_datetime = models.DateTimeField(blank=True, null=True)
    manual_valid_end_datetime = models.DateTimeField(blank=True, null=True)
    user = models.ForeignKey(User, on_delete=CASCADE, related_name='profiles', null=True, blank=True)

    @property
    def is_valid(self):
        now = datetime.now().replace(tzinfo=None)
        if self.actual_valid_start_datetime:
            if self.actual_valid_start_datetime.replace(tzinfo=None) > now:
                return False
        if self.actual_valid_end_datetime:
            if self.actual_valid_end_datetime.replace(tzinfo=None) <= now:
                return False
        return self.actual_is_active

    @property
    def actual_is_active(self):
        return self.is_active if self.manual_is_active is None else self.manual_is_active

    @property
    def actual_valid_start_datetime(self) -> datetime:
        return self.manual_valid_start_datetime or self.valid_start_datetime

    @property
    def actual_valid_end_datetime(self) -> datetime:
        return self.manual_valid_end_datetime or self.valid_end_datetime

    @property
    def cdm_source(self) -> str:
        return self.source
