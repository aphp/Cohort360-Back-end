import logging
import re

from django.db import connections

from cohort.scripts.patch_requests_v130 import NEW_VERSION as PREV_VERSION
from cohort.scripts.query_request_updater import RESOURCE_DEFAULT, MATCH_ALL_VALUES, QueryRequestUpdater

LOGGER = logging.getLogger("info")

NEW_VERSION = "v1.4.0"

FILTER_MAPPING = {
    "Encounter": {
        "_has:Patient:encounter:active": "subject.active",
        "service-provider": "encounter-care-site",
        "destination-type": "admission-destination-type",
        "destination": "discharge-disposition"
    },
    "DocumentReference": {
        "patient-active": "subject.active",
        "encounter-service-provider": "encounter.encounter-care-site"
    },
    "MedicationAdministration": {
        "hierarchy-ATC": "medication",
        "medication-simple": "medication",
        "patient-active": "subject.active",
        "route": "dosage-route",
        "encounter-service-provider": "context.encounter-care-site"
    },
    "MedicationRequest": {
        "hierarchy-ATC": "medication",
        "medication-simple": "medication",
        "patient-active": "subject.active",
        "route": "dosage-instruction-route",
        "type": "category",
        "encounter-service-provider": "encounter.encounter-care-site"
    },
    "Claim": {
        "code": "diagnosis",
        "codeList": "diagnosis",
        "patient-active": "patient.active",
        "encounter-service-provider": "encounter.encounter-care-site"
    },
    "Procedure": {
        "codeList": "code",
        "patient-active": "subject.active",
        "encounter-service-provider": "encounter.encounter-care-site"
    },
    "Condition": {
        "codeList": "code",
        "patient-active": "subject.active",
        "type": "orbis-status",
        "encounter-service-provider": "encounter.encounter-care-site"
    },
    "Observation": {
        "part-of": "code",
        "value-quantity-value": "value-quantity",
        "row_status": "status",
        "encounter-service-provider": "encounter.encounter-care-site",
        "patient-active": "subject.active",
    },
    RESOURCE_DEFAULT: {
    }
}

FILTER_NAME_TO_SKIP = {
    "DocumentReference": ["empty"]
}

UCD_ORBIS_CODESYSTEM = "https://terminology.eds.aphp.fr/aphp-orbis-medicament-code-ucd"
ATC_ORBIS_CODESYSTEM = "https://terminology.eds.aphp.fr/aphp-orbis-medicament-atc-article"
ATC_CODEYSTEM = "https://terminology.eds.aphp.fr/atc"

code_mapping_cache = {
}


def find_related_atc(code: str):
    if code in code_mapping_cache:
        return code_mapping_cache[code]
    LOGGER.info(f"Searching for code {code}")
    cursor = connections["omop"].cursor()
    q = '''
        WITH orbis AS (
            SELECT source_concept_id as orbis_atc_id,source_concept_code as orbis_atc_code 
            FROM omop.concept_fhir 
            WHERE source_vocabulary_reference = %s AND delete_datetime IS NULL
            ),
            atc AS (
            SELECT source_concept_id as atc_id,source_concept_code as atc_code 
            FROM omop.concept_fhir 
            WHERE source_vocabulary_reference = %s AND delete_datetime IS NULL
            )
        SELECT atc_code FROM omop.concept_relationship r
        INNER JOIN orbis o
        ON o.orbis_atc_id = r.concept_id_1
        INNER JOIN atc a
        ON a.atc_id = r.concept_id_2
        WHERE relationship_id = 'Maps to' AND r.delete_datetime IS NULL AND o.orbis_atc_code = %s;
        '''
    cursor.execute(q, (ATC_ORBIS_CODESYSTEM, ATC_CODEYSTEM, code))
    res = cursor.fetchone()
    if not res:
        LOGGER.info(f"Failed to find related atc code {code}")
        if re.match("\\d+", code):
            return UCD_ORBIS_CODESYSTEM + "|" + code
        return ATC_ORBIS_CODESYSTEM + "|" + code
    code_mapping_cache[code] = ATC_CODEYSTEM + "|" + res[0]
    return code_mapping_cache[code]


def find_related_atc_codes(codes: str):
    LOGGER.info(f"Translating codes {codes}")
    return ",".join([find_related_atc(code) for code in codes.split(",")])


FILTER_VALUE_MAPPING = {
    "Observation": {
        "row_status": {
            "Validé": "Val"
        }
    },
    "MedicationRequest": {
        "hierarchy-ATC": {
            MATCH_ALL_VALUES: find_related_atc_codes
        }
    },
    "MedicationAdministration": {
        "hierarchy-ATC": {
            MATCH_ALL_VALUES: find_related_atc_codes
        }
    }
}

STATIC_REQUIRED_FILTERS = {
    "DocumentReference": [
        "contenttype=http://terminology.hl7.org/CodeSystem/v3-mediatypes|text/plain"
    ]
}

RESOURCE_NAME_MAPPING = {
}

updater_v140 = QueryRequestUpdater(
    version_name=NEW_VERSION,
    previous_version_name=PREV_VERSION,
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
