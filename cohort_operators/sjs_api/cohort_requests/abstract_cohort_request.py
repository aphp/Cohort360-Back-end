from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, List

from requests import Response

from accesses.models import Perimeter
from accesses.services.accesses import accesses_service
from admin_cohort.services.auth import auth_service
from admin_cohort.models import User
from cohort_operators.sjs_api.exceptions import FhirException
from cohort_operators.sjs_api.sjs_client import format_spark_job_request_for_sjs
from cohort_operators.sjs_api import Mode, SjsClient, QueryFormatter, SparkJobObject

if TYPE_CHECKING:
    from cohort_operators.sjs_api import CohortQuery


def is_cohort_request_pseudo_read(username: str, source_population: List[int]) -> bool:
    user = User.objects.filter(pk=username).first()
    perimeters = Perimeter.objects.filter(cohort_id__in=source_population)
    return not accesses_service.user_can_access_at_least_one_target_perimeter_in_nomi(user=user, target_perimeters=perimeters)


class AbstractCohortRequest(ABC):
    model = None

    def __init__(self, mode: Mode, sjs_client: SjsClient, auth_headers: dict):
        self.mode = mode
        self.sjs_client = sjs_client
        self.auth_headers = auth_headers

    def __headers_to_owner_entity(self) -> str:
        return auth_service.retrieve_username(token=self.auth_headers['Authorization'].replace('Bearer ', ''),
                                              auth_method=self.auth_headers['authorizationMethod'])

    def create_request_for_sjs(self, cohort_query: CohortQuery) -> str:
        """Format the given query with the Fhir nomenclature and return a dict to be sent
        for the followup sjs request."""
        if cohort_query is None:
            raise FhirException("No query received to format.")

        is_pseudo = is_cohort_request_pseudo_read(username=self.__headers_to_owner_entity(),
                                                  source_population=cohort_query.source_population.care_site_cohort_list)

        sjs_request = QueryFormatter(self.auth_headers).format_to_fhir(cohort_query, is_pseudo)
        cohort_query.criteria = sjs_request

        callback_path = self.mode == Mode.COUNT_WITH_DETAILS and f"/cohort/feasibility-studies/{cohort_query.cohort_uuid}/" or None
        spark_job_request = SparkJobObject(cohort_definition_name="Created from Django",
                                           cohort_definition_syntax=cohort_query,
                                           mode=self.mode,
                                           owner_entity_id=self.__headers_to_owner_entity(),
                                           callbackPath=callback_path)
        return format_spark_job_request_for_sjs(spark_job_request)

    @abstractmethod
    def action(self, cohort_query: CohortQuery) -> Response:
        """Perform the action (count, countAll, create) based on the cohort_query"""
        pass
