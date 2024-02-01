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
    QUESTIONNAIRE_REPONSE = "QuestionnaireReponse"
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
    IMAGING_STUDY_APHP = "imagingStudyAphp"
    QUESTIONNAIRE_RESPONSE_APHP = "questionnaireResponseAphp"
    IPP_LIST = "IPPList"
    PARAMETERS = "parameters"

    @classmethod
    def _missing_(cls, value: str):
        """Get the value comparing to the lower case version of the given string."""
        value = value.lower()
        for member in cls:
            if member.lower() == value:
                return member
        return None
