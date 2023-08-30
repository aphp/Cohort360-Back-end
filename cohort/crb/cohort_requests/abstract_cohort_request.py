from abc import ABC, abstractmethod

from cohort.crb.cohort_query_builder import CohortQueryBuilder
from cohort.crb.enums import Mode
from cohort.crb.fhir_request import FhirRequest
from cohort.crb.sjs_client import SjsClient, format_spark_job_request_for_sjs
from cohort.crb.spark_job_object import SparkJobObject


class AbstractCohortRequest(ABC):
    def __init__(self, mode: Mode, cohort_query_builder: CohortQueryBuilder, sjs_client: SjsClient):
        self.mode = mode
        self.cohort_query_builder: CohortQueryBuilder = cohort_query_builder
        self.sjs_client = sjs_client

    def create_request(self, fhir_request: FhirRequest) -> str:
        spark_job_request = self.cohort_query_builder.create_request(fhir_request, self.mode)
        return self.format_for_sjs(spark_job_request)

    def format_for_sjs(self, spark_job_request: SparkJobObject) -> str:
        return format_spark_job_request_for_sjs(spark_job_request)

    @abstractmethod
    def action(self, fhir_request: FhirRequest) -> str:
        """Perform the action (count, countAll, create) based on the fhir_request"""
        pass
