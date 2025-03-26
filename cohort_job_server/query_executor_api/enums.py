from enum import StrEnum


class Mode(StrEnum):
    COUNT = 'count'
    COUNT_ALL = 'count_all'
    COUNT_WITH_DETAILS = 'count_with_details'
    CREATE = 'create'


class CriteriaType(StrEnum):
    BASIC_RESOURCE = 'basicResource'
    AND_GROUP = 'andGroup'
    OR_GROUP = 'orGroup'
    N_AMONG_M = 'nAmongM'
    REQUEST = 'request'


class ResourceType(StrEnum):
    PATIENT = "Patient"
    CONDITION = "Condition"
    COMPOSITION = "Composition"
    CLAIM = "Claim"
    PROCEDURE = "Procedure"
    SPECIMEN = "Specimen"
    OBSERVATION = "Observation"
    ENCOUNTER = "Encounter"
    MEDICATION_REQUEST = "MedicationRequest"
    MEDICATION_ADMINISTRATION = "MedicationAdministration"
    DOCUMENT_REFERENCE = "DocumentReference"
    IMAGING_STUDY = "ImagingStudy"
    QUESTIONNAIRE_REPONSE = "QuestionnaireResponse"
    IPP_LIST = "IPPList"

    @classmethod
    def _missing_(cls, value: str):
        """Get the value comparing to the lower case version of the given string."""
        value = value.lower()
        for member in cls:
            if member.lower() == value:
                return member
        return None
