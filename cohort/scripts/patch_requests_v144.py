import logging
import sys

from django.db import connections

from cohort.scripts.patch_requests_v140 import NEW_VERSION as PREV_VERSION
from cohort.scripts.patch_requests_v141 import NEW_VERSION as PREV_VERSION_2
from cohort.scripts.query_request_updater import RESOURCE_DEFAULT, MATCH_ALL_VALUES, QueryRequestUpdater, \
    find_mapped_code

LOGGER = logging.getLogger("info")
stream_handler = logging.StreamHandler(stream=sys.stdout)
LOGGER.addHandler(stream_handler)

NEW_VERSION = "v1.4.4"

FILTER_MAPPING = {
    RESOURCE_DEFAULT: {
    }
}

FILTER_NAME_TO_SKIP = {
}

SRC_CODESYSTEM = "https://terminology.eds.aphp.fr/aphp-orbis-cim10"
TARGET_CODEYSTEM = "https://smt.esante.gouv.fr/terminologie-cim-10/"

code_mapping_cache = {
}


def find_related_codes(codes: str):
    LOGGER.info(f"Translating codes {codes}")
    return ",".join([
        find_mapped_code(
            code,
            SRC_CODESYSTEM,
            TARGET_CODEYSTEM,
            lambda c: TARGET_CODEYSTEM + "|NON RENSEIGNE",
            connections["omop"],
            code_mapping_cache
        )
        for code in codes.split(",")])


FILTER_VALUE_MAPPING = {
    "Condition": {
        "code": {
            MATCH_ALL_VALUES: find_related_codes
        }
    }
}

STATIC_REQUIRED_FILTERS = {
}

RESOURCE_NAME_MAPPING = {
}

updater_v144 = QueryRequestUpdater(
    version_name=NEW_VERSION,
    previous_version_name=[PREV_VERSION],
    filter_mapping=FILTER_MAPPING,
    filter_names_to_skip=FILTER_NAME_TO_SKIP,
    filter_values_mapping=FILTER_VALUE_MAPPING,
    static_required_filters=STATIC_REQUIRED_FILTERS,
    resource_name_mapping=RESOURCE_NAME_MAPPING
)
