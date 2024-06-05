from __future__ import annotations

from typing import TYPE_CHECKING

from requests import Response

from cohort.job_server_api.cohort_requests import AbstractCohortRequest
from cohort.job_server_api.enums import Mode
from cohort.models import DatedMeasure

if TYPE_CHECKING:
    from cohort.job_server_api.schemas import CohortQuery


class CohortCount(AbstractCohortRequest):
    model = DatedMeasure

    def __init__(self, *args, **kwargs):
        super().__init__(mode=Mode.COUNT, *args, **kwargs)

    def action(self, cohort_query: CohortQuery) -> Response:
        request = self.create_request_for_sjs(cohort_query)
        return self.sjs_client.count(request)
