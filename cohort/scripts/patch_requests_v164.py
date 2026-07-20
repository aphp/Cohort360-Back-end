import re

from cohort.scripts.patch_requests_v163 import NEW_VERSION as PREV_VERSION
from cohort.scripts.query_request_updater import MATCH_ALL_VALUES, QueryRequestUpdater

NEW_VERSION = "v1.6.4"

# Racine d'un acte, avant segmentation par activité. Cf. guide de lecture CCAM, page 25, section 3.1 :
# https://www.atih.sante.fr/sites/default/files/public/content/1678/guide_lecture_complet_01082008.pdf
CCAM_LEAF_ROOT_RE = re.compile(r"^([A-Z]{4}[0-9]{3})")

CCAM_CODESYSTEMS = frozenset(
    {
        "https://www.atih.sante.fr/plateformes-de-transmission-et-logiciels/logiciels-espace-de-telechargement/id_lot/3550",
        "https://aphp.fr/ig/fhir/core/CodeSystem/CCAMDescriptiveVerAPHP",
        "https://terminology.eds.aphp.fr/aphp-orbis-ccam",
    }
)


def root_prefix_token(token: str) -> str | None:
    if not token or token.endswith("*"):
        return None
    system, sep, code = token.rpartition("|")
    if sep and system not in CCAM_CODESYSTEMS:
        return None
    root = CCAM_LEAF_ROOT_RE.match(code)
    if not root:
        return None
    return f"{system}{sep}{root.group(1)}*"


def map_ccam_codes(codes: str) -> str:
    # Les codes déjà sélectionnés sont conservés : ce sont eux qui restent cochés dans le requêteur.
    mapped: list[str] = []
    for raw_token in codes.split(","):
        token = raw_token.strip()
        if not token:
            continue
        root = root_prefix_token(token)
        # Un acte nu n'existe plus dans le référentiel, le joker le remplace au lieu de s'y ajouter.
        if root and CCAM_LEAF_ROOT_RE.fullmatch(token.rpartition("|")[2]):
            token = root
            root = None
        if token not in mapped:
            mapped.append(token)
        if root and root not in mapped:
            mapped.append(root)
    return ",".join(mapped)


FILTER_MAPPING = {}

FILTER_NAME_TO_SKIP = {}

FILTER_VALUE_MAPPING = {"Procedure": {"code": {MATCH_ALL_VALUES: map_ccam_codes}}}

STATIC_REQUIRED_FILTERS = {}

RESOURCE_NAME_MAPPING = {}


updater_v164 = QueryRequestUpdater(
    version_name=NEW_VERSION,
    previous_version_name=[PREV_VERSION],
    filter_mapping=FILTER_MAPPING,
    filter_names_to_skip=FILTER_NAME_TO_SKIP,
    filter_values_mapping=FILTER_VALUE_MAPPING,
    static_required_filters=STATIC_REQUIRED_FILTERS,
    resource_name_mapping=RESOURCE_NAME_MAPPING,
)
