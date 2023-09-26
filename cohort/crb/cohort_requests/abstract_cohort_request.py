from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from cohort.crb.enums import Mode
from cohort.crb.exceptions import FhirException
from cohort.crb.format_query import FormatQuery
from cohort.crb.sjs_client import SjsClient, format_spark_job_request_for_sjs
from cohort.crb import SparkJobObject

if TYPE_CHECKING:
    from cohort.crb import CohortQuery


class AbstractCohortRequest(ABC):
    def __init__(self, mode: Mode, sjs_client: SjsClient, auth_headers: dict):
        self.mode = mode
        self.sjs_client = sjs_client
        self.auth_headers = auth_headers

    def create_request_for_sjs(self, cohort_query: CohortQuery) -> dict:
        """Format the given query with the Fhir nomenclature and return a dict to be sent
        for the followup sjs request."""
        if cohort_query is None:
            raise FhirException()
        format_query = FormatQuery(self.auth_headers)
        sjs_request = format_query.format_to_fhir(cohort_query)
        cohort_query.request = sjs_request
        spark_job_request = SparkJobObject("Created from Django", cohort_query, self.mode, cohort_query.cohort_uuid)
        return format_spark_job_request_for_sjs(spark_job_request)

    @abstractmethod
    def action(self, cohort_query: CohortQuery) -> dict:
        """Perform the action (count, countAll, create) based on the cohort_query"""
        pass
