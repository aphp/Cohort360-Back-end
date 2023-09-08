from dataclasses import dataclass

from cohort.crb.enums import Mode
from cohort.crb.exceptions import FhirException
from cohort.crb.fhir_request import FhirRequest
from cohort.crb.format_query import FormatQuery
from cohort.crb.spark_job_object import SparkJobObject


@dataclass
class CohortQueryBuilder:
    username: str
    format_query: FormatQuery = FormatQuery()

    def create_request(self, fhir_request: FhirRequest, mode: Mode) -> SparkJobObject:
        if fhir_request is None:
            raise FhirException()
        sjs_request = self.format_query.format_to_fhir(fhir_request)
        fhir_request.request = sjs_request
        return SparkJobObject("Created from Django", fhir_request, mode, self.username)