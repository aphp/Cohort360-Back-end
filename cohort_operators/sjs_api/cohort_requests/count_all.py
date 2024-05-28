from __future__ import annotations

from typing import TYPE_CHECKING

from requests import Response

from accesses.models import Perimeter
from cohort.models import DatedMeasure
from cohort_operators.sjs_api import AbstractCohortRequest, Mode, SourcePopulation

if TYPE_CHECKING:
    from cohort_operators.sjs_api import CohortQuery


class CohortCountAll(AbstractCohortRequest):
    model = DatedMeasure

    def __init__(self, *args, **kwargs):
        super().__init__(mode=Mode.COUNT_ALL, *args, **kwargs)

    def action(self, cohort_query: CohortQuery) -> Response:
        cohort_query.source_population = SourcePopulation(caresiteCohortList=[get_top_care_site_source_population()])
        request = self.create_request_for_sjs(cohort_query)
        return self.sjs_client.count(request)


def get_top_care_site_source_population() -> int:
    return Perimeter.objects.get(level=1, parent__isnull=True).cohort_id
