from __future__ import annotations

import logging
from typing import List, Union

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
    above_levels_ids = models.TextField(blank=True, null=True)
    inferior_levels_ids = models.TextField(blank=True, null=True)
    cohort_id = models.TextField(blank=True, null=True)
    full_path = models.TextField(blank=True, null=True)
    cohort_size = models.TextField(blank=True, null=True)

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
    def all_children_query(self) -> Q:
        return join_qs([Q(
            **{"__".join(i * ["parent"]): self}
        ) for i in range(1, len(PERIMETERS_TYPES))])

    @property
    def all_children_queryset(self) -> QuerySet:
        return Perimeter.objects.filter(self.all_children_query)

    @property
    def above_levels(self):
        if not self.above_levels_ids:
            return list()
        try:
            ids = [int(i) for i in self.above_levels_ids.split(",") if i]
            return ids
        except (AttributeError, ValueError) as e:
            _logger.error(f"Error getting above level ids for perimeter {self}.\n {e}")
            raise e

    @property
    def inferior_levels(self):
        if not self.inferior_levels_ids:
            return list()
        try:
            ids = [int(i) for i in self.inferior_levels_ids.split(",") if i]
            return ids
        except (AttributeError, ValueError) as e:
            _logger.error(f"Error getting inferior level ids for perimeter {self}.\n {e}")
            raise e

    def all_parents_query(self, prefix: str = None) -> Q:
        prefix = f"{prefix}__" if prefix is not None else ""
        return join_qs([
            Q(**{f'{prefix}{"__".join(i * ["children"])}': self})
            for i in range(1, len(PERIMETERS_TYPES))
        ])

    @property
    def all_parents_queryset(self) -> QuerySet:
        return Perimeter.objects.filter(self.all_parents_query()).distinct()

    @classmethod
    def children_prefetch(cls, filtered_queryset: QuerySet = None) -> Prefetch:
        """
        Returns a Prefetch taht can be given to a queryset.prefetch_related
        method to prefetch children and set results to 'prefetched_children'
        :param filtered_queryset: queryset on which filter the result
        of the prefetch
        :return:
        """
        filtered_queryset = filtered_queryset or cls.objects.all()
        return Prefetch('children', queryset=filtered_queryset,
                        to_attr='prefetched_children')


def get_all_perimeters_parents_queryset(perims: List[Perimeter], ) -> QuerySet:
    return Perimeter.objects.filter(join_qs([
        p.all_parents_query() for p in perims
    ]))


def get_all_level_children(
        perimeters_ids: Union[int, List[int]], strict: bool = False,
        filtered_ids: List[str] = [], ids_only: bool = False
) -> List[Union[Perimeter, str]]:
    qs = join_qs(
        [Perimeter.objects.filter(
            **{i * 'parent__' + 'id__in': perimeters_ids}
        ) for i in range(0 + strict, len(PERIMETERS_TYPES))]
    )
    if len(filtered_ids):
        return qs.filter(id__in=filtered_ids)

    if ids_only:
        return [str(i[0]) for i in qs.values_list('id')]
    return list(qs)
