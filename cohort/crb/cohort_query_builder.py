from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from cohort.crb.enums import Mode
from cohort.crb.exceptions import FhirException
from cohort.crb.format_query import FormatQuery
from cohort.crb.spark_job_object import SparkJobObject

if TYPE_CHECKING:
    from cohort.crb import CohortQuery


@dataclass
class CohortQueryBuilder:
    username: str
    format_query: FormatQuery

    def create_request(self, cohort_query: CohortQuery, mode: Mode) -> SparkJobObject:
        if cohort_query is None:
            raise FhirException()
        sjs_request = self.format_query.format_to_fhir(cohort_query)
        cohort_query.request = sjs_request
        return SparkJobObject("Created from Django", cohort_query, mode, self.username)
