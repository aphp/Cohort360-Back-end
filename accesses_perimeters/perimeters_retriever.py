from collections import defaultdict
from typing import List

from django.db import IntegrityError
from django.db.models import QuerySet

from accesses_perimeters.models import FactRelationship
from admin_cohort.models import User


def get_fact_relationships(cohorts_ids: List[str]) -> QuerySet[FactRelationship]:
    return FactRelationship.objects.raw(FactRelationship.sql_get_cohort_source_populations(cohorts_ids))


class PerimetersRetriever:

    @staticmethod
    def get_cohorts_combined_perimeters(cohorts_ids: List[str], owner: User) -> List[int]:
        combined_perimeters = []
        for fact in get_fact_relationships(cohorts_ids):
            if not owner.user_cohorts.filter(group_id=fact.fact_id_1).exists():
                raise IntegrityError(f"The cohort with id={fact.fact_id_1} does not belong to user '{owner.display_name}'")
            combined_perimeters.append(fact.fact_id_2)
        return combined_perimeters

    @staticmethod
    def get_perimeters_per_cohort(cohorts_ids: List[str]) -> dict[str, List[int]]:
        cohort_perimeters = defaultdict(list)
        for fact in get_fact_relationships(cohorts_ids):
            cohort_perimeters[fact.fact_id_1].append(fact.fact_id_2)
        return cohort_perimeters
