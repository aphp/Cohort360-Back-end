from __future__ import annotations

from typing import TYPE_CHECKING

from cohort.crb.cohort_requests.abstract_cohort_request import AbstractCohortRequest
from cohort.crb.enums import Mode

if TYPE_CHECKING:
    from cohort.crb import CohortQuery, SourcePopulation


class CohortCountAll(AbstractCohortRequest):
    def __init__(self, source_population: SourcePopulation, *args, **kwargs):
        super().__init__(mode=Mode.COUNT_ALL, *args, **kwargs)
        self.source_population = source_population

    def action(self, cohort_query: CohortQuery) -> str:
        cohort_query.source_population = self.source_population
        request = self.create_request_for_sjs(cohort_query)
        return self.sjs_client.count(request)

def get_top_care_site_source_population() -> int:
    return Perimeter.objects.get(level=1).cohort_id
