from __future__ import annotations

from typing import TYPE_CHECKING

from requests import Response

from cohort.job_server_api.cohort_requests import AbstractCohortRequest
from cohort.job_server_api.cohort_requests.count_all import get_top_care_site_source_population
from cohort.job_server_api.enums import Mode
from cohort.job_server_api.schemas import SourcePopulation
from cohort.models import FeasibilityStudy

if TYPE_CHECKING:
    from cohort.job_server_api.schemas import CohortQuery


class CohortCountFeasibility(AbstractCohortRequest):
    model = FeasibilityStudy

    def __init__(self, *args, **kwargs):
        super().__init__(mode=Mode.COUNT_WITH_DETAILS, *args, **kwargs)

    def action(self, cohort_query: CohortQuery) -> Response:
        cohort_query.source_population = SourcePopulation(caresiteCohortList=[get_top_care_site_source_population()])
        request = self.create_request_for_sjs(cohort_query)
        return self.sjs_client.count(request)
