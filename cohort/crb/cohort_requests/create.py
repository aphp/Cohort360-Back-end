from __future__ import annotations

from typing import TYPE_CHECKING

from cohort.crb.cohort_requests.abstract_cohort_request import AbstractCohortRequest
from cohort.crb.enums import Mode

if TYPE_CHECKING:
    from cohort.crb import CohortQuery


class CohortCreate(AbstractCohortRequest):
    def __init__(self, *args, **kwargs):
        super().__init__(mode=Mode.CREATE, *args, **kwargs)

    def action(self, cohort_query: CohortQuery) -> str:
        request = self.create_request(cohort_query)
        return self.sjs_client.create(request)

    def cancel(self, job_id: str) -> str:
        return self.sjs_client.delete(job_id)
