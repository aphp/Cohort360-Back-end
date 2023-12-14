from __future__ import annotations

from requests import Response

from cohort.crb import CohortCount, CohortQuery
from cohort.crb.enums import Mode


class CohortCountFeasibility(CohortCount):
    def __init__(self, *args, **kwargs):
        super().__init__(mode=Mode.COUNT_WITH_DETAILS, *args, **kwargs)

    def action(self, cohort_query: CohortQuery) -> tuple[Response, dict]:
        request = self.create_request_for_sjs(cohort_query)
        return self.sjs_client.count(request)
