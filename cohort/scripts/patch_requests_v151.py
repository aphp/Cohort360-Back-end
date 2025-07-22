from cohort.scripts.patch_requests_v150 import NEW_VERSION as PREV_VERSION
from cohort.scripts.query_request_updater import RESOURCE_DEFAULT, QueryRequestUpdater, MATCH_ALL_VALUES


NEW_VERSION = "v1.5.1"

FILTER_MAPPING = {
    RESOURCE_DEFAULT: {
    }
}

FILTER_NAME_TO_SKIP = {
}

code_mapping_cache = {
}


def fix_encounter_filter(filter_value: str):
    return filter_value.replace("encounter.", "")


FILTER_VALUE_MAPPING = {
    "Encounter": {
        "_filter": {
            MATCH_ALL_VALUES: fix_encounter_filter
        }
    }
}

STATIC_REQUIRED_FILTERS = {
}

RESOURCE_NAME_MAPPING = {
}


updater_v151 = QueryRequestUpdater(
    version_name=NEW_VERSION,
    previous_version_name=[PREV_VERSION],
    filter_mapping=FILTER_MAPPING,
    filter_names_to_skip=FILTER_NAME_TO_SKIP,
    filter_values_mapping=FILTER_VALUE_MAPPING,
    static_required_filters=STATIC_REQUIRED_FILTERS,
    resource_name_mapping=RESOURCE_NAME_MAPPING,
)
