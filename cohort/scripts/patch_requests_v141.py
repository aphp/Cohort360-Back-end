import logging

from cohort.scripts.patch_requests_v140 import NEW_VERSION as PREV_VERSION, find_related_atc as find_related_atc_v140, ATC_ORBIS_CODESYSTEM, \
    UCD_ORBIS_CODESYSTEM, ATC_CODEYSTEM
from cohort.scripts.query_request_updater import RESOURCE_DEFAULT, MATCH_ALL_VALUES, QueryRequestUpdater

LOGGER = logging.getLogger("info")

NEW_VERSION = "v1.4.1"

FILTER_MAPPING = {
    RESOURCE_DEFAULT: {
    }
}

FILTER_NAME_TO_SKIP = {
}

code_mapping_cache = {
}


def find_related_atc(code: str):
    if code.startswith(ATC_ORBIS_CODESYSTEM) or code.startswith(UCD_ORBIS_CODESYSTEM) or code.startswith(ATC_CODEYSTEM):
        return code
    return find_related_atc_v140(code)


def find_related_atc_codes(codes: str):
    LOGGER.info(f"Translating codes {codes}")
    return ",".join([find_related_atc(code) for code in codes.split(",")])


FILTER_VALUE_MAPPING = {
    "MedicationRequest": {
        "medication": {
            MATCH_ALL_VALUES: find_related_atc_codes
        }
    },
    "MedicationAdministration": {
        "medication": {
            MATCH_ALL_VALUES: find_related_atc_codes
        }
    }
}

STATIC_REQUIRED_FILTERS = {
}

RESOURCE_NAME_MAPPING = {
}

updater_v141 = QueryRequestUpdater(
    version_name=NEW_VERSION,
    previous_version_name=[PREV_VERSION],
    filter_mapping=FILTER_MAPPING,
    filter_names_to_skip=FILTER_NAME_TO_SKIP,
    filter_values_mapping=FILTER_VALUE_MAPPING,
    static_required_filters=STATIC_REQUIRED_FILTERS,
    resource_name_mapping=RESOURCE_NAME_MAPPING
)


# @dataclasses.dataclass
# class Dummy:
#     serialized_query: str
#
#
# def exec():
#     import json
#     with open("/tmp/cohort_requestquerysnapshot.json", "r") as fh:
#         queries = [Dummy(q["serialized_query"]) for q in json.load(fh)]
#
#
