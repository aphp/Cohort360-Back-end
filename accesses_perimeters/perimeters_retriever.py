import os
from collections import defaultdict
from typing import List

from django.db.models import QuerySet

from accesses_perimeters.models import FactRelationship


env = os.environ

DOMAIN_CONCEPT_ID = env.get("DOMAIN_CONCEPT_COHORT")  # 1147323
RELATIONSHIP_CONCEPT_ID = env.get("FACT_RELATIONSHIP_CONCEPT_COHORT")  # 44818821


def get_fact_relationships(cohorts_ids: List[str]) -> QuerySet[FactRelationship]:
    return FactRelationship.objects.filter(delete_datetime__isnull=True,
                                           domain_concept_id_1=DOMAIN_CONCEPT_ID,
                                           domain_concept_id_2=DOMAIN_CONCEPT_ID,
                                           relationship_concept_id=RELATIONSHIP_CONCEPT_ID,
                                           fact_id_1__in=cohorts_ids)


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
            return fact_relationships. values_list("fact_id_2", flat=True)
