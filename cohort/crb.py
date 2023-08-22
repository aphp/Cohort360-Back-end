import logging

_logger = logging.getLogger("info")
_logger_err = logging.getLogger("django.request")


class FhirRequest:
    ...


class CohortCountAPHP:
    def count(self, fhir_request: FhirRequest) -> str:
        ...


class CRB:
    def __init__(self, cohort_count_aphp: CohortCountAPHP):
        self.cohort_count_aphp = cohort_count_aphp

    def count_all(self, fhir_request: FhirRequest) -> str:
        _logger.info(f"[COUNT_ALL] {fhir_request}")
        return self.cohort_count_aphp.count(fhir_request)
