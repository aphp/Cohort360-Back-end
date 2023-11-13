from __future__ import annotations

import logging

from django.db import models
from django.db.models import Q
from django.db.models.query import QuerySet, Prefetch

from admin_cohort.models import BaseModel
from admin_cohort.settings import PERIMETERS_TYPES
from admin_cohort.tools import join_qs

_logger = logging.getLogger("django.request")


class Perimeter(BaseModel):
    id = models.BigAutoField(primary_key=True)
    local_id = models.CharField(max_length=63, unique=True)
    name = models.TextField(blank=True, null=True)
    source_value = models.TextField(blank=True, null=True)
    short_name = models.TextField(blank=True, null=True)
    type_source_value = models.TextField(blank=True, null=True)
    parent = models.ForeignKey("accesses.perimeter", on_delete=models.CASCADE, related_name="children", null=True)
    above_levels_ids = models.TextField(blank=True, null=True)  # todo: make it ArrayField instead
    inferior_levels_ids = models.TextField(blank=True, null=True)   # todo: make it ArrayField instead
    cohort_id = models.TextField(blank=True, null=True)
    full_path = models.TextField(blank=True, null=True)
    cohort_size = models.TextField(blank=True, null=True)
    level = models.IntegerField(blank=True, null=True)
    count_allowed_users = models.IntegerField(blank=True, null=True, default=0)
    count_allowed_users_inferior_levels = models.IntegerField(blank=True, null=True, default=0)
    count_allowed_users_above_levels = models.IntegerField(blank=True, null=True, default=0)

    def __str__(self):
        return f"[{self.id}] {self.name}"

    @property
    def names(self):
        return dict(name=self.name, short=self.short_name,
                    source_value=self.source_value)

    @property
    def type(self):
        return self.type_source_value

    @property
    def above_levels(self):
        if not self.above_levels_ids:
            return list()
        try:
            return [int(i) for i in self.above_levels_ids.split(",") if i]
        except (AttributeError, ValueError) as e:
            _logger.error(f"Error getting above levels ids for perimeter {self}.\n {e}")
            raise e

    @property
    def inferior_levels(self):
        if not self.inferior_levels_ids:
            return list()
        try:
            return [int(i) for i in self.inferior_levels_ids.split(",") if i]
        except (AttributeError, ValueError) as e:
            _logger.error(f"Error getting inferior levels ids for perimeter {self}.\n {e}")
            raise e

    def q_all_parents(self) -> Q:
        return join_qs([Q(**{f'perimeter__{"__".join(i * ["children"])}': self})
                        for i in range(1, len(PERIMETERS_TYPES))])

    @property
    def all_children(self) -> QuerySet:
        return Perimeter.objects.filter(join_qs([Q(**{"__".join(i * ["parent"]): self})
                                                 for i in range(1, len(PERIMETERS_TYPES))]))
