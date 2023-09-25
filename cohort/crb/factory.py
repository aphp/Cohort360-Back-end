from __future__ import annotations
from typing import TYPE_CHECKING

from cohort.crb.cohort_query_builder import CohortQueryBuilder
from cohort.crb.cohort_requests.count import CohortCount
from cohort.crb.cohort_requests.count_all import CohortCountAll
from cohort.crb.cohort_requests.create import CohortCreate
from cohort.crb.crb import CRB
from cohort.crb.sjs_client import SjsClient

if TYPE_CHECKING:
    from cohort.crb import SourcePopulation


class CRBFactory:
    def __init__(self, cohort_query_builder: CohortQueryBuilder):
        self.sjs_client = SjsClient()
        self.cohort_query_builder = cohort_query_builder

    def create_cohort_count_all(self, source_population: SourcePopulation) -> CRB:
        cohort_count_all = CohortCountAll(cohort_query_builder=self.cohort_query_builder, sjs_client=self.sjs_client)
        return CRB(cohort_action=cohort_count_all)

    def create_cohort_count(self) -> CRB:
        cohort_count = CohortCount(cohort_query_builder=self.cohort_query_builder, sjs_client=self.sjs_client)
        return CRB(cohort_action=cohort_count)

    def create_cohort_create(self) -> CRB:
        cohort_create = CohortCreate(cohort_query_builder=self.cohort_query_builder, sjs_client=self.sjs_client)
        return CRB(cohort_action=cohort_create)
