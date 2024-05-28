from __future__ import annotations

from typing import TYPE_CHECKING

from requests import Response

from cohort.models import DatedMeasure
from cohort_operators.sjs_api import AbstractCohortRequest, Mode

if TYPE_CHECKING:
    from cohort_operators.sjs_api import CohortQuery


class CohortCount(AbstractCohortRequest):
    model = DatedMeasure

    def __init__(self, *args, **kwargs):
        super().__init__(mode=Mode.COUNT, *args, **kwargs)

    def action(self, cohort_query: CohortQuery) -> Response:
        request = self.create_request_for_sjs(cohort_query)
        return self.sjs_client.count(request)
