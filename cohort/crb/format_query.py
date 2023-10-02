from __future__ import annotations
import logging
from typing import TYPE_CHECKING

import requests

from admin_cohort.settings import FHIR_URL
from cohort.crb.enums import CriteriaType, ResourceType
from cohort.crb.exceptions import FhirException
from cohort.crb import FhirParameters

if TYPE_CHECKING:
    from cohort.crb import CohortQuery, Criteria

_logger = logging.getLogger("info")


def query_fhir(resource: str, params: dict[str, list[str]], auth_headers: dict) -> FhirParameters:
    url = f"{FHIR_URL}/{resource}/$query"
    _logger.info(f"Attempting to query fhir with {url=} {params=}")
    response = requests.get(url, params=params, headers=auth_headers)
    response.raise_for_status()
    result = response.json()
    return FhirParameters(**result)


class FormatQuery:
    IDENTIFIER_VALUE = "identifier.value"

    def __init__(self, auth_headers: dict):
        self.auth_headers = auth_headers

    def format_to_fhir(self, cohort_query: CohortQuery) -> Criteria | None:
        def build_solr_criteria(criteria: Criteria, obj) -> Criteria | None:
            if criteria is None:
                return None

            for sub_criteria in criteria.criteria:
                if sub_criteria.criteria_type == CriteriaType.BASIC_RESOURCE:
                    filter_fhir_enriched = sub_criteria.add_criteria(obj)

                    _logger.info(f"filterFhirEnriched {filter_fhir_enriched}")

                    solr_filter, resource_type = self.get_mapping_criteria_filter_fhir_to_solr(
                        sub_criteria.filter_fhir, sub_criteria.resource_type
                    )
                    sub_criteria.filter_solr = solr_filter
                    sub_criteria.resource_type = resource_type
                else:
                    build_solr_criteria(sub_criteria, obj)
            return criteria

        return build_solr_criteria(cohort_query.request, cohort_query.source_population)

    def get_mapping_criteria_filter_fhir_to_solr(
            self, filter_fhir: str, original_resource_type: ResourceType
    ) -> tuple[str, ResourceType]:

        ipp_list_filter = None
        resource_type = original_resource_type
        is_ipp_list = self.is_ipp_list(original_resource_type, filter_fhir)

        if is_ipp_list:
            ipp_list_filter = self.filter_fhir_to_ipp(filter_fhir)
            filter_fhir = self.remove_identifier(filter_fhir)
            resource_type = ResourceType.PATIENT

        fhir_resources_filters = self.call_fhir_resource(resource_type, filter_fhir)
        final_resource_type = original_resource_type if is_ipp_list else fhir_resources_filters['collection']
        full_query = fhir_resources_filters['fq']
        _logger.info(f"FQ: {full_query}")
        return self.merge_fq(full_query, ipp_list_filter), final_resource_type

    def is_ipp_list(self, resource_type, filter_fhir) -> bool:
        return (
                resource_type is not None
                and resource_type.value == ResourceType.IPP_LIST
                and self.IDENTIFIER_VALUE in filter_fhir
        )

    def filter_fhir_to_ipp(self, filter_fhir: str) -> str:
        """Remove identifier value from the filter_fhir"""
        return ''.join([s.replace(f'{self.IDENTIFIER_VALUE}=', '') for s in filter_fhir.split("&")])

    def remove_identifier(self, filter_fhir: str) -> str:
        return "&".join([s for s in filter_fhir.split("&") if self.IDENTIFIER_VALUE not in s])

    def call_fhir_resource(self, resource_type: ResourceType, filter_fhir: str) -> dict:
        if not resource_type:
            raise FhirException(f"Resource type does not exist {resource_type=}, {filter_fhir=}")
        fhir_params: dict[str, list[str]] = {}
        if filter_fhir:
            params = filter_fhir.split("&")
            for param in params:
                key, value = param.split("=")
                if key in fhir_params:
                    fhir_params[key].append(value)
                else:
                    fhir_params[key] = [value]
        params = query_fhir(resource_type, fhir_params, self.auth_headers)
        _logger.info(f"output: {params}")
        return params.to_dict()

    def merge_fq(self, full_query, ipp_list_filter) -> str:
        if ipp_list_filter is None:
            return full_query
        _logger.info("Add Ipp list")
        formatted_filter = ipp_list_filter.replace(",", " ")
        return f"{full_query}&fq={self.IDENTIFIER_VALUE}:({formatted_filter})"
