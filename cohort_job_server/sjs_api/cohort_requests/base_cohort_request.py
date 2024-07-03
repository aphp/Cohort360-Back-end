from __future__ import annotations

import logging
from typing import TYPE_CHECKING, List

from accesses.models import Perimeter
from accesses.services.accesses import accesses_service
from admin_cohort.services.auth import auth_service
from admin_cohort.models import User
from cohort_job_server.sjs_api.exceptions import FhirException
from cohort_job_server.sjs_api.sjs_client import format_spark_job_request_for_sjs
from cohort_job_server.sjs_api import Mode, SJSClient, QueryFormatter, SparkJobObject

if TYPE_CHECKING:
    from cohort_job_server.sjs_api import CohortQuery

_celery_logger = logging.getLogger("celery.app")


class BaseCohortRequest:
    model = None

    def __init__(self, mode: Mode, instance_id: str, json_query: str, auth_headers: dict):
        self.mode = mode
        self.instance_id = instance_id
        self.json_query = json_query
        self.sjs_client = SJSClient()
        self.auth_headers = auth_headers

    def __headers_to_owner_entity(self) -> str:
        return auth_service.retrieve_username(token=self.auth_headers['Authorization'].replace('Bearer ', ''),
                                              auth_method=self.auth_headers['authorizationMethod'])

    @staticmethod
    def is_cohort_request_pseudo_read(username: str, source_population: List[int]) -> bool:
        user = User.objects.filter(pk=username).first()
        perimeters = Perimeter.objects.filter(cohort_id__in=source_population)
        return not accesses_service.user_can_access_at_least_one_target_perimeter_in_nomi(user=user, target_perimeters=perimeters)

    def create_sjs_request(self, cohort_query: CohortQuery) -> str:
        """Format the given query with the Fhir nomenclature and return a dict to be sent
        for the followup sjs request."""
        if cohort_query is None:
            raise FhirException("No query received to format.")

        is_pseudo = self.is_cohort_request_pseudo_read(username=self.__headers_to_owner_entity(),
                                                       source_population=cohort_query.source_population.care_site_cohort_list)

        sjs_request = QueryFormatter(self.auth_headers).format_to_fhir(cohort_query, is_pseudo)
        cohort_query.criteria = sjs_request

        callback_path = self.mode == Mode.COUNT_WITH_DETAILS and f"/cohort/feasibility-studies/{cohort_query.instance_id}/" or None
        spark_job_request = SparkJobObject(cohort_definition_name="Created from Django",
                                           cohort_definition_syntax=cohort_query,
                                           mode=self.mode,
                                           owner_entity_id=self.__headers_to_owner_entity(),
                                           callbackPath=callback_path)
        return format_spark_job_request_for_sjs(spark_job_request)

    def log(self, msg: str) -> None:
        _celery_logger.info(f"Task {self.model}[{self.instance_id}] {msg}")

    def launch(self, cohort_query: CohortQuery):
        """Perform an action (count, countAll, create) based on the cohort_query"""
        self.log(msg=f"Sending request to SJS: {cohort_query}")
