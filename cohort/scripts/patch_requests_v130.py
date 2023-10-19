from cohort.scripts.query_request_updater import QueryRequestUpdater, RESOURCE_DEFAULT

NEW_VERSION = "v1.3.0"

FILTER_MAPPING = {
    "Encounter": {
        "discharge-type": "destination-type",
        "destination": "discharge-disposition",
        "discharge": "discharge-disposition-mode",
        "exitMode": "discharge-disposition-mode",
        "entryMode": "admission-mode",
        "admissionMode": "admission-mode",
        "admitted-from": "admission-mode",
        "priseEnChargeType": "admission-type",
        "typeDeSejour": "admission-type",
        "reason-code": "admission-type",
        "provenance": "admit-source",
        "reason": "reason-code",
        "gender": "_has:Patient:encounter:gender",
        "patient.active": "_has:Patient:encounter:active",
        "patient.birthdate": "_has:Patient:encounter:birthdate",
    },
    "Composition": {
        "status": "docstatus"
    },
    "IPPList": {
        "identifier-simple": "identifier.value"
    },
    RESOURCE_DEFAULT: {
        "patient.active": "patient-active"
    }
}

FILTER_NAME_TO_SKIP = {
    "MedicationRequest": ["medication-simple"],
    "MedicationAdministration": ["medication-simple"],
    "Encounter": ["fileStatus"]
}

FILTER_VALUE_MAPPING = {
    "Condition": {
        "code": {
            "*": "https://terminology.eds.aphp.fr/aphp-orbis-cim10|*"
        }
    },
    "Claim": {
        "code": {
            "*": "https://terminology.eds.aphp.fr/aphp-orbis-ghm|*"
        }
    },
    "Observation": {
        "code": {
            "*": "https://terminology.eds.aphp.fr/aphp-itm-anabio|*"
        }
    },
    "Procedure": {
        "code": {
            "*": "https://terminology.eds.aphp.fr/aphp-orbis-ccam|*"
        }
    }
}

STATIC_REQUIRED_FILTERS = {
    "Claim": [
        "patient-active=true"
    ],
    "Composition": [
        "patient-active=true"
    ],
    "DocumentReference": [
        "patient-active=true"
    ],
    "Condition": [
        "patient-active=true"
    ],
    "Encounter": [
        "_has:Patient:encounter:active=true"
    ],
    "MedicationAdministration": [
        "patient-active=true"
    ],
    "MedicationRequest": [
        "patient-active=true"
    ],
    "Observation": [
        "patient-active=true"
    ],
    "Patient": [
        "active=true"
    ],
    "Procedure": [
        "patient-active=true"
    ]
}

RESOURCE_NAME_MAPPING = {
    "Composition": "DocumentReference"
}

updater_v130 = QueryRequestUpdater(
    version_name=NEW_VERSION,
    previous_version_name=None,
    filter_mapping=FILTER_MAPPING,
    filter_names_to_skip=FILTER_NAME_TO_SKIP,
    filter_values_mapping=FILTER_VALUE_MAPPING,
    static_required_filters=STATIC_REQUIRED_FILTERS,
    resource_name_mapping=RESOURCE_NAME_MAPPING
)
