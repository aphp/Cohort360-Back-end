from __future__ import annotations

from typing import TYPE_CHECKING

from requests import Response

from cohort_job_server.sjs_api import BaseCohortRequest, Mode
from cohort.models import CohortResult

if TYPE_CHECKING:
    from cohort_job_server.sjs_api import CohortQuery


class CohortCreate(BaseCohortRequest):
    model = CohortResult

    def __init__(self, *args, **kwargs):
        super().__init__(mode=Mode.CREATE, *args, **kwargs)

    def launch(self, cohort_query: CohortQuery) -> Response:
        request = self.create_sjs_request(cohort_query)
        return self.sjs_client.create(request)

    def cancel(self, job_id: str) -> Response:
        return self.sjs_client.delete(job_id)
