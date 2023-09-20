from cohort.patches.query_request_updater import QueryRequestUpdater, RESOURCE_DEFAULT

NEW_VERSION = "v1.4.0"

FILTER_MAPPING = {
    "Encounter": {
        "_has:Patient:encounter:active": "subject.active"
    },
    "DocumentReference": {
        "patient-active": "subject.active"
    },
    "MedicationAdministration": {
        "hierarchy-ATC": "medication-hierarchy",
        "medication-simple": "medication",
        "patient-active": "subject.active"
    },
    "MedicationRequest": {
        "hierarchy-ATC": "medication-hierarchy",
        "medication-simple": "medication",
        "patient-active": "subject.active"
    },
    "Claim": {
        "code": "diagnosis",
        "codeList": "diagnosis-hierarchy",
        "patient-active": "patient.active"
    },
    "Procedure": {
        "codeList": "code-hierarchy",
        "patient-active": "subject.active"
    },
    "Condition": {
        "codeList": "code-hierarchy",
        "patient-active": "subject.active"
    },
    "Observation": {
        "part-of": "code-hierarchy",
        "value-quantity-value": "value-quantity",
        "row_status": "status",
        "encounter-service-provider": "encounter.encounter-care-site",
        "patient-active": "subject.active"
    },
    RESOURCE_DEFAULT: {
    }
}

FILTER_NAME_TO_SKIP = {
    "DocumentReference": ["empty"]
}

FILTER_VALUE_MAPPING = {
    "Observation": {
        "row_status": {
            "Validé": "Val"
        }
    }
}

STATIC_REQUIRED_FILTERS = {
    "DocumentReference": [
        "contenttype=http%3A%2F%2Fterminology.hl7.org%2FCodeSystem%2Fv3-mediatypes%7Ctext%2Fplain"
    ]
}

RESOURCE_NAME_MAPPING = {
}

updater_v140 = QueryRequestUpdater(
    version_name=NEW_VERSION,
    filter_mapping=FILTER_MAPPING,
    filter_names_to_skip=FILTER_NAME_TO_SKIP,
    filter_values_mapping=FILTER_VALUE_MAPPING,
    static_required_filters=STATIC_REQUIRED_FILTERS,
    resource_name_mapping=RESOURCE_NAME_MAPPING
)
