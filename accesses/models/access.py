from __future__ import annotations

import datetime
from typing import List, Dict

from django.db import models
from django.db.models import CASCADE, SET_NULL
from django.utils.datetime_safe import date, datetime as dt

from accesses.models.perimeter import Perimeter
from accesses.models.profile import Profile
from accesses.models.role import Role
from admin_cohort.tools.cache import invalidate_cache
from admin_cohort.models import BaseModel, User
from admin_cohort.settings import MANUAL_SOURCE


class Access(BaseModel):
    id = models.BigAutoField(primary_key=True)
    perimeter = models.ForeignKey(Perimeter, on_delete=SET_NULL, related_name='accesses', null=True)
    profile = models.ForeignKey(Profile, on_delete=CASCADE, related_name='accesses', null=True)
    role = models.ForeignKey(Role, on_delete=CASCADE, related_name='accesses', null=True)
    source = models.TextField(blank=True, null=True, default=MANUAL_SOURCE)
    start_datetime = models.DateTimeField(blank=True, null=True)
    end_datetime = models.DateTimeField(blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=SET_NULL, related_name='created_accesses', null=True, db_column="created_by")
    updated_by = models.ForeignKey(User, on_delete=SET_NULL, related_name='updated_accesses', null=True, db_column="updated_by")

    def save(self, *args, **kwargs):
        super(Access, self).save(*args, **kwargs)
        related_models = [f.related_model.__name__ for f in Access._meta.fields if f.is_relation]
        for model in related_models:
            invalidate_cache(model_name=model)

    @property
    def is_valid(self):
        now = datetime.datetime.now(tz=datetime.timezone.utc)
        valid = True
        if self.start_datetime:
            if isinstance(self.start_datetime, date):
                start_datetime = dt.combine(self.start_datetime, dt.min)
            else:
                start_datetime = self.start_datetime
            if start_datetime > now:
                valid = False
        if self.end_datetime:
            if isinstance(self.end_datetime, date):
                end_datetime = dt.combine(self.end_datetime, dt.min)
            else:
                end_datetime = self.end_datetime
            if end_datetime <= now:
                valid = False
        return valid

    @property
    def care_site_id(self):
        return self.perimeter.id

    @property
    def care_site(self):
        return {
            'care_site_id': self.perimeter.id,
            'care_site_name': self.perimeter.name,
            'care_site_short_name': self.perimeter.short_name,
            'care_site_type_source_value': self.perimeter.type_source_value,
            'care_site_source_value': self.perimeter.source_value,
        } if self.perimeter else None

    @property
    def accesses_criteria_to_exclude(self) -> List[Dict]:
        res = self.role.unreadable_rights

        for read_r in (self.role.inf_level_readable_rights + self.role.same_level_readable_rights):
            d = {read_r: True}

            if read_r in self.role.inf_level_readable_rights:
                d['perimeter_not_child'] = [self.perimeter_id]

            if read_r in self.role.same_level_readable_rights:
                d['perimeter_not'] = [self.perimeter_id]

            res.append(d)

        return res
