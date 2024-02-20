from __future__ import annotations

from typing import TYPE_CHECKING

from requests import Response

from cohort.crb.cohort_requests.abstract_cohort_request import AbstractCohortRequest
from cohort.crb.enums import Mode
from cohort.models import DatedMeasure

if TYPE_CHECKING:
    from cohort.crb.schemas import CohortQuery


class CohortCount(AbstractCohortRequest):
    model = DatedMeasure

    def __init__(self, *args, **kwargs):
        super().__init__(mode=Mode.COUNT, *args, **kwargs)

    def action(self, cohort_query: CohortQuery) -> tuple[Response, dict]:
        request = self.create_request_for_sjs(cohort_query)
        return self.sjs_client.count(request)
