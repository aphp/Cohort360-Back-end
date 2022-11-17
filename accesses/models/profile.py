from __future__ import annotations

from django.db import models
from django.db.models import CASCADE, Q
from django.utils import timezone
from django.utils.datetime_safe import datetime

from admin_cohort.models import BaseModel, User
from admin_cohort.settings import MANUAL_SOURCE


class Profile(BaseModel):
    id = models.AutoField(blank=True, null=False, primary_key=True)
    provider_id = models.BigIntegerField(blank=True, null=True)
    provider_name = models.TextField(blank=True, null=True)
    firstname = models.TextField(blank=True, null=True)
    lastname = models.TextField(blank=True, null=True)
    email = models.TextField(blank=True, null=True)
    source = models.TextField(blank=True, null=True, default=MANUAL_SOURCE)

    is_active = models.BooleanField(blank=True, null=True)
    manual_is_active = models.BooleanField(blank=True, null=True)
    valid_start_datetime: datetime = models.DateTimeField(blank=True,
                                                          null=True)
    manual_valid_start_datetime: datetime = models.DateTimeField(
        blank=True, null=True)
    valid_end_datetime: datetime = models.DateTimeField(blank=True,
                                                        null=True)
    manual_valid_end_datetime: datetime = models.DateTimeField(
        blank=True, null=True)

    user = models.ForeignKey(User, on_delete=CASCADE,
                             related_name='profiles',
                             null=True, blank=True)

    class Meta:
        managed = True

    @property
    def is_valid(self):
        now = datetime.now().replace(tzinfo=None)
        if self.actual_valid_start_datetime is not None:
            if self.actual_valid_start_datetime.replace(tzinfo=None) > now:
                return False
        if self.actual_valid_end_datetime is not None:
            if self.actual_valid_end_datetime.replace(tzinfo=None) <= now:
                return False
        return self.actual_is_active

    @property
    def actual_is_active(self):
        return self.is_active if self.manual_is_active is None \
            else self.manual_is_active

    @property
    def actual_valid_start_datetime(self) -> datetime:
        return self.valid_start_datetime \
            if self.manual_valid_start_datetime is None \
            else self.manual_valid_start_datetime

    @property
    def actual_valid_end_datetime(self) -> datetime:
        return self.valid_end_datetime \
            if self.manual_valid_end_datetime is None \
            else self.manual_valid_end_datetime

    @property
    def cdm_source(self) -> str:
        return str(self.source)

    @classmethod
    def Q_is_valid(cls, field_prefix: str = '') -> Q:
        """
        Returns a query Q on Profile fields (can go with a prefix)
        Filtering on validity :
        - (valid_start or manual_valid_start if exist) is before now or null
        - (valid_end or manual_valid_end if exist) is after now or null
        - (active or manual_active if exist) is True
        :param field_prefix: str set before each field in case the queryset is
        used when Profile is a related object
        :return:
        """
        # now = datetime.now().replace(tzinfo=None)
        now = timezone.now()
        field_prefix = f"{field_prefix}__" if field_prefix else ""
        fields = dict(
            valid_start=f"{field_prefix}valid_start_datetime",
            manual_valid_start=f"{field_prefix}manual_valid_start_datetime",
            valid_end=f"{field_prefix}valid_end_datetime",
            manual_valid_end=f"{field_prefix}manual_valid_end_datetime",
            active=f"{field_prefix}is_active",
            manual_active=f"{field_prefix}manual_is_active",
        )
        q_actual_start_is_none = Q(**{
            fields['valid_start']: None,
            fields['manual_valid_start']: None
        })
        q_start_lte_now = ((Q(**{fields['manual_valid_start']: None})
                            & Q(**{f"{fields['valid_start']}__lte": now}))
                           | Q(
                    **{f"{fields['manual_valid_start']}__lte": now}))

        q_actual_end_is_none = Q(**{
            fields['valid_end']: None,
            fields['manual_valid_end']: None
        })
        q_end_gte_now = ((Q(**{fields['manual_valid_end']: None})
                          & Q(**{f"{fields['valid_end']}__gte": now}))
                         | Q(**{f"{fields['manual_valid_end']}__gte": now}))

        q_is_active = ((Q(**{fields['manual_active']: None})
                        & Q(**{fields['active']: True}))
                       | Q(**{fields['manual_active']: True}))
        return ((q_actual_start_is_none | q_start_lte_now)
                & (q_actual_end_is_none | q_end_gte_now)
                & q_is_active)
