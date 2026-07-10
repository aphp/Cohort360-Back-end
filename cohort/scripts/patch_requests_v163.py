from cohort.scripts.patch_requests_v162 import NEW_VERSION as PREV_VERSION
from cohort.scripts.query_request_updater import MATCH_ALL_VALUES, QueryRequestUpdater

NEW_VERSION = "v1.6.3"

# "000001 - ARBORESCENCE CCAM" était la racine du référentiel, désormais supprimée : une requête qui la portait
# doit couvrir tout le CCAM. Les codes feuilles segmentés sont traités à l'exécution, pas ici.
CCAM_ROOT_CODE = "000001"


def code_part(token: str) -> str:
    return token.split("|", 1)[1] if "|" in token else token


def replace_ccam_root_with_match_all(codes: str) -> str:
    return ",".join("*" if code_part(token.strip()) == CCAM_ROOT_CODE else token for token in codes.split(","))


FILTER_MAPPING = {}

FILTER_NAME_TO_SKIP = {}

FILTER_VALUE_MAPPING = {"Procedure": {"code": {MATCH_ALL_VALUES: replace_ccam_root_with_match_all}}}

STATIC_REQUIRED_FILTERS = {}

RESOURCE_NAME_MAPPING = {}


updater = QueryRequestUpdater(
    version_name=NEW_VERSION,
    previous_version_name=[PREV_VERSION],
    filter_mapping=FILTER_MAPPING,
    filter_names_to_skip=FILTER_NAME_TO_SKIP,
    filter_values_mapping=FILTER_VALUE_MAPPING,
    static_required_filters=STATIC_REQUIRED_FILTERS,
    resource_name_mapping=RESOURCE_NAME_MAPPING,
)
