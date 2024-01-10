from __future__ import annotations

from typing import TYPE_CHECKING

from requests import Response

from cohort.crb import AbstractCohortRequest
from cohort.crb.cohort_requests.count_all import get_top_care_site_source_population
from cohort.crb.enums import Mode
from cohort.crb.schemas import SourcePopulation

if TYPE_CHECKING:
    from cohort.crb.schemas import CohortQuery


class CohortCountFeasibility(AbstractCohortRequest):
    def __init__(self, *args, **kwargs):
        super().__init__(mode=Mode.COUNT_WITH_DETAILS, *args, **kwargs)

    def action(self, cohort_query: CohortQuery) -> tuple[Response, dict]:
        cohort_query.source_population = SourcePopulation(caresiteCohortList=[get_top_care_site_source_population()])
        cohort_query.callbackPath = f"/cohort/feasibility-studies/{cohort_query.cohort_uuid}/"
        request = self.create_request_for_sjs(cohort_query)
        return self.sjs_client.count(request)
