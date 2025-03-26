from __future__ import annotations

from typing import TYPE_CHECKING

from requests import Response

from cohort.models import FeasibilityStudy
from cohort_job_server.query_executor_api.cohort_requests.base_cohort_request import BaseCohortRequest, Mode
from cohort_job_server.query_executor_api.cohort_requests.cohort_count_all import get_top_care_site_source_population
from cohort_job_server.query_executor_api import SourcePopulation

if TYPE_CHECKING:
    from cohort_job_server.query_executor_api import CohortQuery


class FeasibilityCount(BaseCohortRequest):
    model = FeasibilityStudy

    def __init__(self, *args, **kwargs):
        super().__init__(mode=Mode.COUNT_WITH_DETAILS, *args, **kwargs)

    def launch(self, cohort_query: CohortQuery) -> Response:
        super().launch(cohort_query)
        cohort_query.source_population = SourcePopulation(caresiteCohortList=[get_top_care_site_source_population()])
        request = self.create_query_executor_request(cohort_query)
        return self.query_executor_client.count(request)
