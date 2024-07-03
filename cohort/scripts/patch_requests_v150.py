import logging
import sys
import urllib.parse
from typing import Any

from cohort.scripts.patch_requests_v144 import NEW_VERSION as PREV_VERSION
from cohort.scripts.query_request_updater import RESOURCE_DEFAULT, QueryRequestUpdater

LOGGER = logging.getLogger("info")
stream_handler = logging.StreamHandler(stream=sys.stdout)
LOGGER.addHandler(stream_handler)

NEW_VERSION = "v1.5.0"

FILTER_MAPPING = {
    RESOURCE_DEFAULT: {
    }
}

FILTER_NAME_TO_SKIP = {
}

code_mapping_cache = {
}

FILTER_VALUE_MAPPING = {
}

STATIC_REQUIRED_FILTERS = {
}

RESOURCE_NAME_MAPPING = {
}

RESOURCE_DATE_MAPPING = {
    "Condition": "recorded-date",
    "Procedure": "date",
    "Claim": "created",
    "DocumentReference": "date",
    "MedicationRequest": "validity-period-start",
    "MedicationAdministration": "effective-time",
    "ImagingStudy": "started",
    "Observation": "date",
    "QuestionnaireResponse": "authored",
    "Encounter": "period-start"
}


def replace_date_options_with_filter(query: Any) -> bool:
    def add_null_filter(allow_null, filter_value):
        if allow_null:
            filter_param_value = "({}) or not (date eq \"*\")".format(filter_value)
            return "_filter={}".format(urllib.parse.quote(filter_param_value))
        return filter_value

    resource = query["resourceType"]
    if "dateRangeList" in query:
        if resource not in RESOURCE_DATE_MAPPING:
            logging.error(f"Resource {resource} does not have a date field")
            return False
        date_range_option = query["dateRangeList"]
        allow_null_date = "dateIsNotNull" not in date_range_option or date_range_option["dateIsNotNull"]
        filters = []
        if "minDate" in date_range_option:
            filters.append("{}{}{}".format(RESOURCE_DATE_MAPPING[resource], " gt " if allow_null_date else "=gt",
                                           query["dateRangeList"]["minDate"]))
        if "maxDate" in date_range_option:
            filters.append("{}{}{}".format(RESOURCE_DATE_MAPPING[resource], " lt " if allow_null_date else "=lt",
                                           query["dateRangeList"]["maxDate"]))
        if filters:
            query["filterFhir"] = query.get("filterFhir", "")
            has_already_filter = query["filterFhir"].strip() != ""
            join = "&" if has_already_filter else ""
            query["filterFhir"] += join + add_null_filter(allow_null_date,
                                                          " and ".join(
                                                              filters) if allow_null_date else "&".join(
                                                              filters))
            return True
    return False


updater_v150 = QueryRequestUpdater(
    version_name=NEW_VERSION,
    previous_version_name=[PREV_VERSION],
    filter_mapping=FILTER_MAPPING,
    filter_names_to_skip=FILTER_NAME_TO_SKIP,
    filter_values_mapping=FILTER_VALUE_MAPPING,
    static_required_filters=STATIC_REQUIRED_FILTERS,
    resource_name_mapping=RESOURCE_NAME_MAPPING,
    post_process_basic_resource=replace_date_options_with_filter
)
