from collections import defaultdict
from typing import List

from django.db.models import QuerySet

from accesses_perimeters.models import FactRelationship


def get_fact_relationships(cohorts_ids: List[str]) -> QuerySet[FactRelationship]:
    return FactRelationship.objects.raw(FactRelationship.sql_get_cohort_source_populations(cohorts_ids))


class PerimetersRetriever:

    @staticmethod
    def get_cohorts_combined_perimeters(cohorts_ids: List[str]) -> List[int]:
        return get_fact_relationships(cohorts_ids).values_list("fact_id_2", flat=True)

    @staticmethod
    def get_perimeters_per_cohort(cohorts_ids: List[str]) -> dict[str, List[int]]:
        cohort_perimeters = defaultdict(list)
        for fact in get_fact_relationships(cohorts_ids):
            cohort_perimeters[fact.fact_id_1].append(fact.fact_id_2)
        return cohort_perimeters
