from __future__ import annotations
from typing import List, Dict

from django.db import models
from django.db.models import CASCADE, Q, SET_NULL
from django.utils import timezone
from django.utils.datetime_safe import datetime

from accesses.models.perimeter import Perimeter
from accesses.models.profile import Profile
from accesses.models.role import Role
from admin_cohort.models import BaseModel
from admin_cohort.settings import MANUAL_SOURCE


class Access(BaseModel):
    id = models.BigAutoField(primary_key=True)
    perimeter = models.ForeignKey(
        Perimeter, to_field='id', on_delete=SET_NULL,
        related_name='accesses', null=True)
    source = models.TextField(blank=True, null=True, default=MANUAL_SOURCE)

    start_datetime = models.DateTimeField(blank=True, null=True)
    end_datetime = models.DateTimeField(blank=True, null=True)
    manual_start_datetime = models.DateTimeField(blank=True, null=True)
    manual_end_datetime = models.DateTimeField(blank=True, null=True)

    profile = models.ForeignKey(Profile, on_delete=CASCADE,
                                related_name='accesses', null=True)
    role: Role = models.ForeignKey(Role, on_delete=CASCADE,
                                   related_name='accesses', null=True)

    @property
    def is_valid(self):
        today = datetime.now()
        if self.actual_start_datetime is not None:
            actual_start_datetime = datetime.combine(
                self.actual_start_datetime.date()
                if isinstance(self.actual_start_datetime, datetime) else
                self.actual_start_datetime,
                datetime.min
            )
            if actual_start_datetime > today:
                return False
        if self.actual_end_datetime is not None:
            actual_end_datetime = datetime.combine(
                self.actual_end_datetime.date()
                if isinstance(self.actual_end_datetime, datetime)
                else self.actual_end_datetime,
                datetime.min
            )
            if actual_end_datetime <= today:
                return False
        return True

    @classmethod
    def Q_is_valid(cls) -> Q:
        # now = datetime.now().replace(tzinfo=None)
        now = timezone.now()
        q_actual_start_is_none = Q(start_datetime=None,
                                   manual_start_datetime=None)
        q_start_lte_now = ((Q(manual_start_datetime=None)
                            & Q(start_datetime__lte=now))
                           | Q(manual_start_datetime__lte=now))

        q_actual_end_is_none = Q(end_datetime=None,
                                 manual_end_datetime=None)
        q_end_gte_now = ((Q(manual_end_datetime=None)
                          & Q(end_datetime__gte=now))
                         | Q(manual_end_datetime__gte=now))
        return ((q_actual_start_is_none | q_start_lte_now)
                & (q_actual_end_is_none | q_end_gte_now))

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
    def actual_start_datetime(self):
        return self.start_datetime if self.manual_start_datetime is None \
            else self.manual_start_datetime

    @property
    def actual_end_datetime(self):
        return self.end_datetime if self.manual_end_datetime is None \
            else self.manual_end_datetime

    @property
    def accesses_criteria_to_exclude(self) -> List[Dict]:
        res = self.role.unreadable_rights

        for read_r in (self.role.inf_level_readable_rights
                       + self.role.same_level_readable_rights):
            d = {read_r: True}

            if read_r in self.role.inf_level_readable_rights:
                d['perimeter_not_child'] = [self.perimeter_id]

            if read_r in self.role.same_level_readable_rights:
                d['perimeter_not'] = [self.perimeter_id]

            res.append(d)

        return res

    class Meta:
        managed = True
