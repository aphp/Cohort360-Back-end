from __future__ import annotations

import os
from typing import TYPE_CHECKING

from requests import Response

from accesses.models import Perimeter
from cohort.crb.schemas import SourcePopulation
from cohort.crb.cohort_requests.abstract_cohort_request import AbstractCohortRequest
from cohort.crb.enums import Mode
from cohort.models import DatedMeasure

if TYPE_CHECKING:
    from cohort.crb.schemas import CohortQuery

env = os.environ


class CohortCountAll(AbstractCohortRequest):
    model = DatedMeasure

    def __init__(self, *args, **kwargs):
        super().__init__(mode=Mode.COUNT_ALL, *args, **kwargs)

    def action(self, cohort_query: CohortQuery) -> tuple[Response, dict]:
        cohort_query.source_population = SourcePopulation(caresiteCohortList=[get_top_care_site_source_population()])
        request = self.create_request_for_sjs(cohort_query)
        return self.sjs_client.count(request)


def get_top_care_site_source_population() -> int:
    return Perimeter.objects.get(level=1, parent__isnull=True).cohort_id
