from enum import StrEnum


class Mode(StrEnum):
    COUNT = 'count'
    COUNT_ALL = 'count_all'
    CREATE = 'create'


class CriteriaType(StrEnum):
    BASIC_RESOURCE = 'basic_resource'
    AND_GROUP = 'and_group'
    OR_GROUP = 'or_group'
    N_AMONG_M = 'n_among_m'
    REQUEST = 'request'


class ResourceType(StrEnum):
    PATIENT = "patient"
    CONDITION = "condition"
    COMPOSITION = "composition"
    CLAIM = "claim"
    PROCEDURE = "procedure"
    SPECIMEN = "specimen"
    OBSERVATION = "observation"
    ENCOUNTER = "encounter"
    MEDICATION_REQUEST = "medication_request"
    MEDICATION_ADMINISTRATION = "medication_administration"
    DOCUMENT_REFERENCE = "document_reference"
    PATIENT_APHP = "patient_aphp"
    CLAIM_APHP = "claim_aphp"
    COMPOSITION_APHP = "composition_aphp"
    PROCEDURE_APHP = "procedure_aphp"
    OBSERVATION_APHP = "observation_aphp"
    ENCOUNTER_APHP = "encounter_aphp"
    MEDICATION_REQUEST_APHP = "medication_request_aphp"
    MEDICATION_ADMINISTRATION_APHP = "medication_administration_aphp"
    DOCUMENT_REFERENCE_APHP = "document_reference_aphp"
    CONDITION_APHP = "condition_aphp"
    IPP_LIST = "ipp_list"
