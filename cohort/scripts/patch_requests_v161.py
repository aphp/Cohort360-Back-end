import logging
import sys

from cohort.scripts.patch_requests_v160 import NEW_VERSION as PREV_VERSION
from cohort.scripts.query_request_updater import RESOURCE_DEFAULT, QueryRequestUpdater

LOGGER = logging.getLogger("info")
stream_handler = logging.StreamHandler(stream=sys.stdout)
LOGGER.addHandler(stream_handler)

NEW_VERSION = "v1.6.1"

FILTER_MAPPING = {
    "MedicationAdministration": {
        "medication": "code",
    },
    "MedicationRequest": {
        "medication": "code"
    },
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


updater_v161 = QueryRequestUpdater(
    version_name=NEW_VERSION,
    previous_version_name=[PREV_VERSION],
    filter_mapping=FILTER_MAPPING,
    filter_names_to_skip=FILTER_NAME_TO_SKIP,
    filter_values_mapping=FILTER_VALUE_MAPPING,
    static_required_filters=STATIC_REQUIRED_FILTERS,
    resource_name_mapping=RESOURCE_NAME_MAPPING,
)
