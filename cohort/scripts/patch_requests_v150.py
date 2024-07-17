import logging
import sys
import urllib.parse
from typing import Any

from cohort.scripts.patch_requests_v145 import NEW_VERSION as PREV_VERSION
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

RESOURCE_ENCOUNTER_DATE_MAPPING = {
    "Condition": "encounter.period-start",
    "Procedure": "encounter.period-start",
    "Claim": "encounter.period-start",
    "DocumentReference": "encounter.period-start",
    "MedicationRequest": "encounter.period-start",
    "MedicationAdministration": "context.period-start",
    "ImagingStudy": "encounter.period-start",
    "Observation": "encounter.period-start",
    "QuestionnaireResponse": "encounter.period-start",
    "Encounter": "encounter.period-start"
}


def add_null_filter(allow_null, date_field_name, filter_value):
    if allow_null:
        filter_param_value = "({}) or not ({} eq \"*\")".format(filter_value, date_field_name)
        return "_filter={}".format(urllib.parse.quote(filter_param_value))
    return filter_value


def update_filter(date_range, query, date_field):
    allow_null_date = "dateIsNotNull" not in date_range or date_range["dateIsNotNull"]
    filters = []
    if "minDate" in date_range:
        filters.append("{}{}{}".format(date_field, " gt " if allow_null_date else "=gt",
                                       date_range["minDate"]))
    if "maxDate" in date_range:
        filters.append("{}{}{}".format(date_field, " lt " if allow_null_date else "=lt",
                                       date_range["maxDate"]))
    if filters:
        query["filterFhir"] = query.get("filterFhir", "")
        has_already_filter = query["filterFhir"].strip() != ""
        join = "&" if has_already_filter else ""
        query["filterFhir"] += join + add_null_filter(allow_null_date, date_field,
                                                      " and ".join(
                                                          filters) if allow_null_date else "&".join(
                                                          filters))


def replace_date_options_with_filter(query: Any) -> bool:
    resource = query["resourceType"]
    has_changed = False
    if "dateRangeList" in query:
        if resource not in RESOURCE_DATE_MAPPING:
            logging.error(f"Resource {resource} does not have a date field")
        else:
            date_range_option = query["dateRangeList"]
            for date_range in date_range_option:
                update_filter(date_range, query, RESOURCE_DATE_MAPPING[resource])
                has_changed = True
    if "encounterDateRange" in query:
        if resource not in RESOURCE_ENCOUNTER_DATE_MAPPING:
            logging.error(f"Resource {resource} does not have a date field")
        else:
            update_filter(query["encounterDateRange"], query, RESOURCE_ENCOUNTER_DATE_MAPPING[resource])
            has_changed = True
    return has_changed


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
