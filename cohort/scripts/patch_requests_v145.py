from typing import List, Optional

from cohort.scripts.patch_requests_v144 import NEW_VERSION as PREV_VERSION
from cohort.scripts.query_request_updater import RESOURCE_DEFAULT, QueryRequestUpdater


NEW_VERSION = "v1.4.5"

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


def return_filter_if_not_exist(filters: List[str], filter_name: str, filter_value: str) -> Optional[str]:
    filter_names = [f.split("=")[0] for f in filters]
    if filter_name not in filter_names:
        return f"{filter_name}={filter_value}"
    return None


STATIC_REQUIRED_FILTERS = {
    "Observation": [
        lambda filters: return_filter_if_not_exist(filters, "value-quantity", "ge0,le0")
    ]
}

RESOURCE_NAME_MAPPING = {
}


updater_v145 = QueryRequestUpdater(
    version_name=NEW_VERSION,
    previous_version_name=[PREV_VERSION],
    filter_mapping=FILTER_MAPPING,
    filter_names_to_skip=FILTER_NAME_TO_SKIP,
    filter_values_mapping=FILTER_VALUE_MAPPING,
    static_required_filters=STATIC_REQUIRED_FILTERS,
    resource_name_mapping=RESOURCE_NAME_MAPPING,
)
