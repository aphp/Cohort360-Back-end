from __future__ import annotations

import logging
from typing import TYPE_CHECKING, List, Optional

from accesses.models import Perimeter
from accesses.services.accesses import accesses_service
from admin_cohort.models import User
from cohort_job_server.sjs_api.exceptions import FhirException
from cohort_job_server.sjs_api.schemas import ModeOptions
from cohort_job_server.sjs_api.sjs_client import format_spark_job_request_for_sjs
from cohort_job_server.sjs_api import Mode, SJSClient, QueryFormatter, SparkJobObject

if TYPE_CHECKING:
    from cohort_job_server.sjs_api import CohortQuery

_celery_logger = logging.getLogger("celery.app")


class BaseCohortRequest:
    model = None

    def __init__(self, mode: Mode,
                 instance_id: Optional[str],
                 json_query: str,
                 auth_headers: dict,
                 callback_path: str = None,
                 existing_cohort_id: int = None,
                 owner_username: str = None,
                 sampling_ratio: Optional[float] = None,
                 stage_details: Optional[str] = None):
        self.mode = mode
        self.instance_id = instance_id
        self.json_query = json_query
        self.sjs_client = SJSClient()
        self.auth_headers = auth_headers
        self.callback_path = callback_path
        self.owner_username = owner_username
        self.existing_cohort_id = existing_cohort_id
        self.sampling_ratio = sampling_ratio
        self.stage_details = stage_details

    @staticmethod
    def is_cohort_request_pseudo_read(username: str, source_population: List[int]) -> bool:
        user = User.objects.filter(pk=username).first()
        perimeters = Perimeter.objects.filter(cohort_id__in=source_population)
        return not accesses_service.user_can_access_at_least_one_target_perimeter_in_nomi(user=user,
                                                                                          target_perimeters=perimeters)

    def create_sjs_request(self, cohort_query: CohortQuery) -> str:
        """Format the given query with the Fhir nomenclature and return a dict to be sent
        for the followup sjs request."""
        if cohort_query is None:
            raise FhirException("No query received to format.")

        is_pseudo = self.is_cohort_request_pseudo_read(username=self.owner_username,
                                                       source_population=cohort_query.source_population.care_site_cohort_list)

        sjs_request = QueryFormatter(self.auth_headers).format_to_fhir(cohort_query, is_pseudo)
        cohort_query.criteria = sjs_request

        callback_path = self.callback_path or (
                self.mode == Mode.COUNT_WITH_DETAILS and f"/cohort/feasibility-studies/{cohort_query.instance_id}/" or None)
        spark_job_request = SparkJobObject(cohort_definition_name="Created from C360 backend",
                                           cohort_definition_syntax=cohort_query,
                                           mode=self.mode,
                                           owner_entity_id=self.owner_username,
                                           callbackPath=callback_path,
                                           existingCohortId=self.existing_cohort_id,
                                           modeOptions=(self.sampling_ratio or self.stage_details) and
                                                       ModeOptions(sampling=self.sampling_ratio, details=self.stage_details) or None
                                           )
        return format_spark_job_request_for_sjs(spark_job_request)

    def log(self, msg: str) -> None:
        _celery_logger.info(f"Task {self.model.__name__}[{self.instance_id}] {msg}")

    def launch(self, cohort_query: CohortQuery):
        """Perform an action (count, countAll, create) based on the cohort_query"""
        self.log(msg=f"Sending request to SJS: {cohort_query}")
