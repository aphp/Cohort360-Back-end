from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from admin_cohort.auth.utils import get_userinfo_from_token
from cohort.crb.enums import Mode
from cohort.crb.exceptions import FhirException
from cohort.crb.query_formatter import QueryFormatter
from cohort.crb.schemas import SparkJobObject
from cohort.crb.sjs_client import SjsClient, format_spark_job_request_for_sjs

if TYPE_CHECKING:
    from cohort.crb.schemas import CohortQuery


class AbstractCohortRequest(ABC):
    def __init__(self, mode: Mode, sjs_client: SjsClient, auth_headers: dict):
        self.mode = mode
        self.sjs_client = sjs_client
        self.auth_headers = auth_headers

    def __headers_to_owner_entity(self) -> str:
        user = get_userinfo_from_token(
            self.auth_headers['Authorization'].replace('Bearer ', ''),
            self.auth_headers['authorizationMethod']
        )
        return user.username

    def create_request_for_sjs(self, cohort_query: CohortQuery) -> str:
        """Format the given query with the Fhir nomenclature and return a dict to be sent
        for the followup sjs request."""
        if cohort_query is None:
            raise FhirException("No query received to format.")

        sjs_request = QueryFormatter(self.auth_headers).format_to_fhir(cohort_query)
        cohort_query.criteria = sjs_request

        spark_job_request = SparkJobObject(
            "Created from Django", cohort_query, self.mode, self.__headers_to_owner_entity()
        )
        return format_spark_job_request_for_sjs(spark_job_request)

    @abstractmethod
    def action(self, cohort_query: CohortQuery) -> dict:
        """Perform the action (count, countAll, create) based on the cohort_query"""
        pass
