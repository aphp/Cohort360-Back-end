from cohort.scripts.patch_requests_v161 import NEW_VERSION as PREV_VERSION
from cohort.scripts.query_request_updater import RESOURCE_DEFAULT, MATCH_ALL_VALUES, QueryRequestUpdater

NEW_VERSION = "v1.6.2"

FILTER_MAPPING = {RESOURCE_DEFAULT: {}}

FILTER_NAME_TO_SKIP = {}

CCAM_OLD_CODESYSTEM = "https://www.atih.sante.fr/plateformes-de-transmission-et-logiciels/logiciels-espace-de-telechargement/id_lot/3550"
CCAM_NEW_CODESYSTEM = "https://aphp.fr/ig/fhir/core/CodeSystem/CCAMDescriptiveVerAPHP"


def map_ccam_code_token(code_token: str) -> str:
    token = code_token.strip()
    if not token:
        return token

    if "|" in token:
        system, code = token.split("|", 1)
        if system == CCAM_NEW_CODESYSTEM:
            return token
        if system != CCAM_OLD_CODESYSTEM:
            return token
    else:
        code = token

    return f"{CCAM_NEW_CODESYSTEM}|{code}"


def map_ccam_codes(codes: str) -> str:
    return ",".join([map_ccam_code_token(code_token) for code_token in codes.split(",")])


FILTER_VALUE_MAPPING = {"Procedure": {"code": {MATCH_ALL_VALUES: map_ccam_codes}}}

STATIC_REQUIRED_FILTERS = {}

RESOURCE_NAME_MAPPING = {}


updater_v162 = QueryRequestUpdater(
    version_name=NEW_VERSION,
    previous_version_name=[PREV_VERSION],
    filter_mapping=FILTER_MAPPING,
    filter_names_to_skip=FILTER_NAME_TO_SKIP,
    filter_values_mapping=FILTER_VALUE_MAPPING,
    static_required_filters=STATIC_REQUIRED_FILTERS,
    resource_name_mapping=RESOURCE_NAME_MAPPING,
)
