from __future__ import annotations

import logging
import os
import urllib.parse
from typing import TYPE_CHECKING

import requests
from django.conf import settings

from admin_cohort.http_timeout import HTTP_REQUEST_TIMEOUT
from admin_cohort.middleware.context_request_middleware import get_trace_id
from cohort_job_server.apps import CohortJobServerConfig
from cohort_job_server.query_executor_api.enums import CriteriaType, ResourceType
from cohort_job_server.query_executor_api.exceptions import FhirException
from cohort_job_server.query_executor_api.schemas import FhirParameters

if TYPE_CHECKING:
    from cohort_job_server.query_executor_api.schemas import CohortQuery, Criteria, SourcePopulation

env = os.environ
FHIR_URL = env.get("FHIR_URL")
SECURITY_PSEUDED = "_security=http://terminology.hl7.org/CodeSystem/v3-ObservationValue|PSEUDED"

logger = logging.getLogger(__name__)


def query_fhir(resource: str, params: dict[str, list[str]], auth_headers: dict) -> FhirParameters:
    url = f"{FHIR_URL}/{resource}/$query"

    # this additional query is made to the real endpoint because the $query one does not check for params
    if CohortJobServerConfig.TEST_FHIR_QUERIES:
        url_test = f"{FHIR_URL}/{resource}"
        logger.info(f"Testing real fhir query with {url_test=} {params=}")
        response = requests.get(url_test, params={**params, "_count": 0}, headers=auth_headers, timeout=HTTP_REQUEST_TIMEOUT)
        response.raise_for_status()

    logger.info(f"Attempting to query fhir with {url=} {params=}")

    auth_headers[settings.TRACE_ID_HEADER] = get_trace_id()

    response = requests.get(url, params=params, headers=auth_headers, timeout=HTTP_REQUEST_TIMEOUT)
    response.raise_for_status()
    result = response.json()
    return FhirParameters(**result)


def add_security_params_to_filter_fhir(sub_criteria: Criteria, source_population: SourcePopulation, is_pseudo: bool) -> str | None:
    if sub_criteria.filter_fhir is None:
        return None
    params = []
    if is_pseudo and sub_criteria.resource_type != ResourceType.IPP_LIST:
        params.append(SECURITY_PSEUDED)
    if source_population is not None:
        params.append(source_population.format_to_fhir())
    params.append(sub_criteria.filter_fhir)
    return "&".join(param for param in params if param)


# Procedure ne porte que du CCAM (EDS), donc un token sans système est du CCAM legacy.
CCAM_CODESYSTEMS = frozenset(
    {
        "https://www.atih.sante.fr/plateformes-de-transmission-et-logiciels/logiciels-espace-de-telechargement/id_lot/3550",
        "https://terminology.eds.aphp.fr/aphp-orbis-ccam",
        "https://aphp.fr/ig/fhir/core/CodeSystem/CCAMDescriptiveVerAPHP",
    }
)


def prefix_ccam_leaf_code(token: str) -> str:
    # Le référentiel CCAM a été ré-encodé (segmentation des actes, suffixe de niveau sur les
    # noeuds) : un code stocké ne matche plus à l'identique, quel que soit son format. On le
    # cherche donc en préfixe, sauf s'il porte déjà un `*` ou un système non-CCAM.
    system, sep, code = token.rpartition("|")
    if sep and system not in CCAM_CODESYSTEMS:
        return token
    if not code or code.endswith("*"):
        return token
    return f"{system}{sep}{code}*"


def add_prefix_search_on_ccam_leaves(filter_fhir: str, resource_type: ResourceType) -> str:
    if not filter_fhir or resource_type != ResourceType.PROCEDURE:
        return filter_fhir
    params = []
    for param in filter_fhir.split("&"):
        key, sep, value = param.partition("=")
        base, _, modifier = key.partition(":")
        # `code:in` / `code:not-in` portent une URI de ValueSet, pas des codes : on ne les touche pas.
        if sep and base == "code" and modifier in ("", "not"):
            value = ",".join(prefix_ccam_leaf_code(token) for token in value.split(","))
        params.append(f"{key}{sep}{value}")
    return "&".join(params)


class QueryFormatter:
    IDENTIFIER_VALUE = "identifier.value"

    def __init__(self, auth_headers: dict):
        self.auth_headers = auth_headers

    def format_to_fhir(self, cohort_query: CohortQuery, is_pseudo: bool) -> Criteria | None:

        def build_solr_criteria(criteria: Criteria, source_population: SourcePopulation) -> Criteria | None:
            if criteria is None:
                return None

            if criteria.criteria_type == CriteriaType.BASIC_RESOURCE:
                criteria.filter_fhir = add_prefix_search_on_ccam_leaves(criteria.filter_fhir, criteria.resource_type)
                filter_fhir_enriched = add_security_params_to_filter_fhir(criteria, source_population, is_pseudo)

                logger.info(f"filterFhirEnriched {filter_fhir_enriched}")

                if CohortJobServerConfig.USE_SOLR:
                    solr_filter = self.get_mapping_criteria_filter_fhir_to_solr(filter_fhir_enriched, criteria.resource_type)
                    criteria.filter_solr = solr_filter
                return criteria

            for sub_criteria in criteria.criteria:
                build_solr_criteria(sub_criteria, source_population)
            return criteria

        return build_solr_criteria(cohort_query.criteria, cohort_query.source_population)

    def get_mapping_criteria_filter_fhir_to_solr(self, filter_fhir: str, original_resource_type: ResourceType) -> str:

        ipp_list_filter = None
        resource_type = original_resource_type
        is_ipp_list = self.is_ipp_list(original_resource_type, filter_fhir)

        if is_ipp_list:
            ipp_list_filter = self.filter_fhir_to_ipp(filter_fhir)
            filter_fhir = self.remove_identifier(filter_fhir)
            resource_type = ResourceType.PATIENT

        fhir_resources_filters = self.call_fhir_resource(resource_type, filter_fhir)
        full_query = fhir_resources_filters["fq"]
        logger.info(f"FQ: {full_query}")
        return self.merge_fq(full_query, ipp_list_filter)

    def is_ipp_list(self, resource_type: ResourceType, filter_fhir: str) -> bool:
        return resource_type == ResourceType.IPP_LIST and self.IDENTIFIER_VALUE in (filter_fhir or "")

    def filter_fhir_to_ipp(self, filter_fhir: str) -> str:
        """Extract the identifier values from the filter_fhir"""
        return ",".join([s.replace(f"{self.IDENTIFIER_VALUE}=", "") for s in filter_fhir.split("&") if self.IDENTIFIER_VALUE in s])

    def remove_identifier(self, filter_fhir: str) -> str:
        return "&".join([s for s in filter_fhir.split("&") if self.IDENTIFIER_VALUE not in s])

    def call_fhir_resource(self, resource_type: ResourceType, filter_fhir: str) -> dict:
        if not resource_type:
            raise FhirException(f"Resource type does not exist {resource_type=}, {filter_fhir=}")
        fhir_params: dict[str, list[str]] = {}
        if filter_fhir:
            params = filter_fhir.split("&")
            for param in params:
                if not param:
                    continue
                key, value = param.split("=")
                # because the filter_fhir we received has its value already urlencoded
                decoded_value = urllib.parse.unquote(value)
                if key in fhir_params:
                    fhir_params[key].append(decoded_value)
                else:
                    fhir_params[key] = [decoded_value]
        params = query_fhir(resource_type, fhir_params, self.auth_headers)
        logger.info(f"output: {params}")
        return params.to_dict()

    def merge_fq(self, full_query, ipp_list_filter) -> str:
        if ipp_list_filter is None:
            return full_query
        logger.info("Add Ipp list")
        formatted_filter = ipp_list_filter.replace(",", " ")
        return f"{full_query}&fq={self.IDENTIFIER_VALUE}:({formatted_filter})"
