from __future__ import annotations

from functools import cached_property

from django.db import models
from django.db.models import CASCADE, SET_NULL
from django.utils import timezone
from django.conf import settings

from accesses.models import Perimeter, Profile, Role
from admin_cohort.tools.cache import invalidate_cache
from admin_cohort.models import BaseModel, User


class Access(BaseModel):
    id = models.BigAutoField(primary_key=True)
    perimeter = models.ForeignKey(Perimeter, on_delete=SET_NULL, related_name='accesses', null=True)
    profile = models.ForeignKey(Profile, on_delete=CASCADE, related_name='accesses', null=True)
    role = models.ForeignKey(Role, on_delete=CASCADE, related_name='accesses', null=True)
    source = models.TextField(blank=True, null=True, default=settings.MANUAL_SOURCE)
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
        now = timezone.now()
        if self.start_datetime > now or self.end_datetime <= now:
            return False
        return True

    @cached_property
    def care_site_id(self):
        return self.perimeter.id

    @cached_property
    def care_site(self):
        return {'care_site_id': self.perimeter.id,
                'care_site_name': self.perimeter.name,
                'care_site_short_name': self.perimeter.short_name,
                'care_site_type_source_value': self.perimeter.type_source_value,
                'care_site_source_value': self.perimeter.source_value,
                } if self.perimeter else None
