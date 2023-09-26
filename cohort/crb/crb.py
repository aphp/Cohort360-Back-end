from __future__ import annotations

from typing import TYPE_CHECKING

from cohort.crb.cohort_requests.abstract_cohort_request import AbstractCohortRequest

if TYPE_CHECKING:
    from cohort.crb import CohortQuery


class CRB:
    def __init__(self, cohort_action: AbstractCohortRequest):
        self.cohort_action = cohort_action

    def request_to_sjs(self, fhir_request: CohortQuery) -> dict:
        return self.cohort_action.action(fhir_request)
