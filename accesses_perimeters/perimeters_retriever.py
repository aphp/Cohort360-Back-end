from collections import defaultdict
from typing import List

from django.db.models import QuerySet

from accesses_perimeters.models import FactRelationship


def get_fact_relationships(cohorts_ids: List[str]) -> QuerySet[FactRelationship]:
    return FactRelationship.objects.raw(FactRelationship.sql_get_cohort_source_populations(cohorts_ids))


class PerimetersRetriever:

    @staticmethod
    def get_virtual_cohorts(cohorts_ids: List[str], group_by_cohort_id: bool) -> dict[str, List[int]] | QuerySet[List[int]]:
        fact_relationships = get_fact_relationships(cohorts_ids)
        if group_by_cohort_id:
            cohort_perimeters = defaultdict(list)
            for fact in fact_relationships:
                cohort_perimeters[fact.fact_id_1].append(fact.fact_id_2)
            return cohort_perimeters
        else:
            return fact_relationships.values_list("fact_id_2", flat=True)
