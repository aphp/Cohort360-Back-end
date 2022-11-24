from django.db.models import QuerySet

from accesses.models import Perimeter, Access, Role
from accesses.tools.perimeter_process import get_perimeters_ids_list
from cohort.models import CohortResult

ROLE = "role"
READ_PATIENT_NOMI = "read_patient_nomi"
READ_PATIENT_PSEUDO = "read_patient_pseudo"
EXPORT_CSV_NOMI = "export_csv_nomi"
EXPORT_CSV_PSEUDO = "export_csv_pseudo"
EXPORT_JUPYTER_NOMI = "export_jupyter_nomi"
EXPORT_JUPYTER_PSEUDO = "export_jupyter_pseudo"
SEARCH_IPP = "search_ipp"


def get_dict_right_accesses(user_accesses: [Access]) -> dict:
    return {READ_PATIENT_NOMI: user_accesses.filter(Role.is_read_patient_role_nominative(ROLE)),
            READ_PATIENT_PSEUDO: user_accesses.filter(Role.is_read_patient_role_pseudo(ROLE)),
            EXPORT_CSV_NOMI: user_accesses.filter(Role.is_export_csv_nominative_role(ROLE)),
            EXPORT_CSV_PSEUDO: user_accesses.filter(Role.is_export_csv_pseudo_role(ROLE)),
            EXPORT_JUPYTER_NOMI: user_accesses.filter(Role.is_export_jupyter_nominative_role(ROLE)),
            EXPORT_JUPYTER_PSEUDO: user_accesses.filter(Role.is_export_jupyter_pseudo_role(ROLE)),
            SEARCH_IPP: user_accesses.filter(Role.is_search_ipp_role(ROLE))}


def is_right_on_accesses(accesses: QuerySet, perimeter_ids: [int]):
    if accesses.filter(perimeter_id__in=perimeter_ids):
        return True
    return False


def get_max_perimeter_dict_right(perimeter: Perimeter, accesses: dict):
    above_levels_ids = get_perimeters_ids_list(perimeter.above_levels_ids)
    above_levels_ids.append(perimeter.id)
    perimeter_dict_right = {}
    for key, value in accesses:
        perimeter_dict_right[key] = is_right_on_accesses(accesses[key], above_levels_ids)
    return perimeter_dict_right


def get_right_default_dict():
    return {READ_PATIENT_NOMI: True,
            READ_PATIENT_PSEUDO: True,
            EXPORT_CSV_NOMI: True,
            EXPORT_CSV_PSEUDO: True,
            EXPORT_JUPYTER_NOMI: True,
            EXPORT_JUPYTER_PSEUDO: True,
            SEARCH_IPP: True}


def dict_boolean_and(dict_1: dict, dict_2: dict):
    and_dict = {}
    for key, value in dict_1:
        and_dict[key] = value and dict_2[key]
    return and_dict


def get_rights_from_cohort(accesses_dict: dict, cohort: CohortResult) -> dict:
    perimeters = Perimeter.objects.filter(cohort_id=cohort.fhir_group_id)
    right_dict = get_right_default_dict()
    for perimeter in perimeters:
        perimeter_right_dict = get_max_perimeter_dict_right(perimeter, accesses_dict)
        right_dict = dict_boolean_and(right_dict, perimeter_right_dict)
    return right_dict


def get_all_cohorts_rights(user_accesses: [Access], cohort_list: [CohortResult]):
    response_list = []
    accesses_dict = get_dict_right_accesses(user_accesses)
    for cohort in cohort_list:
        rights = get_rights_from_cohort(accesses_dict, cohort)
        response_list.append(CohortRights(cohort.fhir_group_id, rights))

    return response_list


# ------------------------- CLASS DEFINITION -------------------------
class CohortRights:
    def __init__(self, cohort_id, rights_dict, **kwargs):
        """
        @return: a default DataRight as required by the serializer
        """
        self.cohort_id = cohort_id
        self.rights = rights_dict
