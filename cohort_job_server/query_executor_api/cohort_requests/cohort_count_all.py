from __future__ import annotations

from typing import TYPE_CHECKING

from requests import Response

from accesses.models import Perimeter
from cohort.models import DatedMeasure
from cohort_job_server.query_executor_api.cohort_requests.base_cohort_request import BaseCohortRequest, Mode
from cohort_job_server.query_executor_api import SourcePopulation

if TYPE_CHECKING:
    from cohort_job_server.query_executor_api import CohortQuery


def get_top_care_site_source_population() -> int:
    return Perimeter.objects.get(level=1, parent__isnull=True).cohort_id


class CohortCountAll(BaseCohortRequest):
    model = DatedMeasure

    def __init__(self, *args, **kwargs):
        super().__init__(mode=Mode.COUNT_ALL, *args, **kwargs)

    def launch(self, cohort_query: CohortQuery) -> Response:
        super().launch(cohort_query)
        cohort_query.source_population = SourcePopulation(caresiteCohortList=[get_top_care_site_source_population()])
        request = self.create_query_executor_request(cohort_query)
        return self.query_executor_client.count(request)
