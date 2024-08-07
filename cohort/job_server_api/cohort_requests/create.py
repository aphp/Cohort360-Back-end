from __future__ import annotations

from typing import TYPE_CHECKING

from requests import Response

from cohort.job_server_api.cohort_requests import AbstractCohortRequest
from cohort.job_server_api.enums import Mode
from cohort.models import CohortResult

if TYPE_CHECKING:
    from cohort.job_server_api.schemas import CohortQuery


class CohortCreate(AbstractCohortRequest):
    model = CohortResult

    def __init__(self, *args, **kwargs):
        super().__init__(mode=Mode.CREATE, *args, **kwargs)

    def action(self, cohort_query: CohortQuery) -> Response:
        request = self.create_request_for_sjs(cohort_query)
        return self.sjs_client.create(request)

    def cancel(self, job_id: str) -> Response:
        return self.sjs_client.delete(job_id)