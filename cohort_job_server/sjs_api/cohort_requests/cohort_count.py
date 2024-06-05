from __future__ import annotations

from typing import TYPE_CHECKING

from requests import Response

from cohort.models import DatedMeasure
from cohort_job_server.sjs_api.cohort_requests.base_cohort_request import BaseCohortRequest, Mode

if TYPE_CHECKING:
    from cohort_job_server.sjs_api import CohortQuery


class CohortCount(BaseCohortRequest):
    model = DatedMeasure

    def __init__(self, *args, **kwargs):
        super().__init__(mode=Mode.COUNT, *args, **kwargs)

    def launch(self, cohort_query: CohortQuery) -> Response:
        super().launch(cohort_query)
        request = self.create_sjs_request(cohort_query)
        return self.sjs_client.count(request)
