import logging

import requests

from admin_cohort.settings import SJS_URL
from cohort.crb.enums import CriteriaType, ResourceType
from cohort.crb.fhir_params import FhirParameters
from cohort.crb.fhir_request import FhirRequest
from cohort.crb.ranges import Criteria

_logger = logging.getLogger("info")
_logger_err = logging.getLogger("django.request")


def query_fhir(resource: str, params: dict[str, list[str]]) -> FhirParameters:
    url = f"{SJS_URL}/{resource}"
    response = requests.get(url, params=params)
    response.raise_for_status()
    result = response.json()
    # return resp, result


class FormatQuery:
    IDENTIFIER_VALUE = "identifier.value"

    def format_to_fhir(self, fhir_request: FhirRequest) -> Criteria | None:
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

        return build_solr_criteria(fhir_request.request, fhir_request.source_population)

    def get_mapping_criteria_filter_fhir_to_solr(
            self, filter_fhir: str, resource_type: ResourceType
    ) -> tuple[str, ResourceType]:

        ipp_list_filter = None
        is_ipp_list = self.is_ipp_list(resource_type, filter_fhir)
        if is_ipp_list:
            ipp_list_filter = self.filter_fhir_to_ipp(filter_fhir)
            filter_fhir = self.remove_identifier(filter_fhir)
            resource_type = ResourceType.PATIENT

        fhir_resources_filters = self.call_fhir_resource(resource_type, filter_fhir)
        if is_ipp_list:
            resource_type = fhir_resources_filters['collection']
        full_query = fhir_resources_filters['fq']
        _logger.info(f"FQ: {full_query}")
        return self.merge_fq(full_query, ipp_list_filter), resource_type

    def is_ipp_list(self, resource_type, filter_fhir) -> bool:
        return (
                resource_type is not None
                and resource_type.value != ResourceType.IPP_LIST
                and self.IDENTIFIER_VALUE in filter_fhir
        )

    def filter_fhir_to_ipp(self, filter_fhir: str) -> str:
        """Remove identifier value from the filter_fhir"""
        return ''.join([s.replace(f'{self.IDENTIFIER_VALUE}=', '') for s in filter_fhir.split("&")])

    def remove_identifier(self, filter_fhir: str) -> str:
        return "&".join([s for s in filter_fhir.split("&") if self.IDENTIFIER_VALUE not in s])

    def call_fhir_resource(self, resource_type: ResourceType, filter_fhir: str) -> FhirParameters:
        if not resource_type:
            raise ...
        fhir_params: dict[str, list[str]] = {}
        if filter_fhir:
            params = filter_fhir.split("&")
            for param in params:
                key, value = param.split("=")
                if key in fhir_params:
                    fhir_params[key].append(value)
                else:
                    fhir_params[key] = [value]
        params = query_fhir(resource_type, fhir_params)
        _logger.info(f"output: {params}")
        return params

    def merge_fq(self, full_query, ipp_list_filter) -> str:
        if ipp_list_filter is None:
            return full_query
        _logger.info("Add Ipp list")
        formatted_filter = ipp_list_filter.replace(",", " ")
        return f"{full_query}&fq={self.IDENTIFIER_VALUE}:({formatted_filter})"
