from enum import StrEnum


class Mode(StrEnum):
    COUNT = 'count'
    COUNT_ALL = 'countAll'
    CREATE = 'create'


class CriteriaType(StrEnum):
    BASIC_RESOURCE = 'basicResource'
    AND_GROUP = 'andGroup'
    OR_GROUP = 'orGroup'
    N_AMONG_M = 'nAmongM'
    REQUEST = 'request'


class ResourceType(StrEnum):
    PATIENT = "Patient"
    CONDITION = "condition"
    COMPOSITION = "composition"
    CLAIM = "claim"
    PROCEDURE = "procedure"
    SPECIMEN = "specimen"
    OBSERVATION = "observation"
    ENCOUNTER = "encounter"
    MEDICATION_REQUEST = "medicationRequest"
    MEDICATION_ADMINISTRATION = "medicationAdministration"
    DOCUMENT_REFERENCE = "documentReference"
    PATIENT_APHP = "patientAphp"
    CLAIM_APHP = "claimAphp"
    COMPOSITION_APHP = "compositionAphp"
    PROCEDURE_APHP = "procedureAphp"
    OBSERVATION_APHP = "observationAphp"
    ENCOUNTER_APHP = "encounterAphp"
    MEDICATION_REQUEST_APHP = "medicationRequestAphp"
    MEDICATION_ADMINISTRATION_APHP = "medicationAdministrationAphp"
    DOCUMENT_REFERENCE_APHP = "documentReferenceAphp"
    CONDITION_APHP = "conditionAphp"
    IPP_LIST = "ippList"
    PARAMETERS = "parameters"

    @classmethod
    def _missing_(cls, value: str):
        """Get the value comparing to the lower case version of the given string."""
        value = value.lower()
        for member in cls:
            if member.lower() == value:
                return member
        return None
