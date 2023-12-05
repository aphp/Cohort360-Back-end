import logging

from django.db import connections

from cohort.scripts.patch_requests_v140 import NEW_VERSION as PREV_VERSION
from cohort.scripts.patch_requests_v141 import NEW_VERSION as PREV_VERSION_2
from cohort.scripts.query_request_updater import RESOURCE_DEFAULT, MATCH_ALL_VALUES, QueryRequestUpdater

LOGGER = logging.getLogger("info")

NEW_VERSION = "v1.4.2"

FILTER_MAPPING = {
    RESOURCE_DEFAULT: {
    }
}

FILTER_NAME_TO_SKIP = {
    "DocumentReference": ["empty"]
}

ORBIS_CODESYSTEM = "https://terminology.eds.aphp.fr/aphp-orbis-ccam"
ATIH_CODEYSTEM = "https://www.atih.sante.fr/plateformes-de-transmission-et-logiciels/logiciels-espace-de-telechargement/id_lot/3550"

code_mapping_cache = {
}


def find_related_atih(code: str):
    if code in code_mapping_cache:
        return code_mapping_cache[code]
    LOGGER.info(f"Searching for code {code}")
    cursor = connections["omop"].cursor()
    q = '''
        WITH orbis AS (
            SELECT source_concept_id as orbis_id,source_concept_code as orbis_code 
            FROM omop.concept_fhir 
            WHERE source_vocabulary_reference = %s AND delete_datetime IS NULL
            ),
            atih AS (
            SELECT source_concept_id as atih_id,source_concept_code as atih_code 
            FROM omop.concept_fhir 
            WHERE source_vocabulary_reference = %s AND delete_datetime IS NULL
            )
        SELECT atih_code FROM omop.concept_relationship r
        INNER JOIN orbis o
        ON o.orbis_id = r.concept_id_1
        INNER JOIN atih a
        ON a.atih_id = r.concept_id_2
        WHERE relationship_id = 'Maps to' AND r.delete_datetime IS NULL AND o.orbis_atc_code = %s;
        '''
    cursor.execute(q, (ORBIS_CODESYSTEM, ATIH_CODEYSTEM, code))
    res = cursor.fetchone()
    if not res:
        LOGGER.info(f"Failed to find related atc code {code}")
        code_mapping_cache[code] = ATIH_CODEYSTEM + "|NON RENSEIGNE"
        return code_mapping_cache[code]
    code_mapping_cache[code] = ATIH_CODEYSTEM + "|" + res[0]
    return code_mapping_cache[code]


def find_related_atih_codes(codes: str):
    LOGGER.info(f"Translating codes {codes}")
    return ",".join([find_related_atih(code) for code in codes.split(",")])


FILTER_VALUE_MAPPING = {
    "Procedure": {
        "code": {
            MATCH_ALL_VALUES: find_related_atih_codes
        }
    }
}

STATIC_REQUIRED_FILTERS = {
}

RESOURCE_NAME_MAPPING = {
}

updater_v142 = QueryRequestUpdater(
    version_name=NEW_VERSION,
    previous_version_name=[PREV_VERSION, PREV_VERSION_2],
    filter_mapping=FILTER_MAPPING,
    filter_names_to_skip=FILTER_NAME_TO_SKIP,
    filter_values_mapping=FILTER_VALUE_MAPPING,
    static_required_filters=STATIC_REQUIRED_FILTERS,
    resource_name_mapping=RESOURCE_NAME_MAPPING
)
