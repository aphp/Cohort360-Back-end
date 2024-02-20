from __future__ import annotations

from typing import TYPE_CHECKING

from requests import Response

from cohort.crb.cohort_requests.abstract_cohort_request import AbstractCohortRequest
from cohort.crb.enums import Mode
from cohort.models import CohortResult

if TYPE_CHECKING:
    from cohort.crb.schemas import CohortQuery


class CohortCreate(AbstractCohortRequest):
    model = CohortResult

    def __init__(self, *args, **kwargs):
        super().__init__(mode=Mode.CREATE, *args, **kwargs)

    def action(self, cohort_query: CohortQuery) -> tuple[Response, dict]:
        request = self.create_request_for_sjs(cohort_query)
        return self.sjs_client.create(request)

    def cancel(self, job_id: str) -> str:
        return self.sjs_client.delete(job_id)
