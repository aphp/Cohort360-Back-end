from typing import List

from django.db.models import QuerySet

from accesses.models import Perimeter, Role
from accesses.tools import get_user_valid_manual_accesses
from admin_cohort.models import User
from cohort.tools import get_list_cohort_id_care_site


class PerimeterReadRight:
    def __init__(self,
                 perimeter: Perimeter,
                 read_nomi: bool = False,
                 read_pseudo: bool = False,
                 allow_search_by_ipp: bool = False,
                 allow_read_opposed_patient: bool = False):
        self.perimeter = perimeter
        self.right_read_patient_nominative = read_nomi
        self.right_read_patient_pseudonymized = read_pseudo
        self.right_search_patients_by_ipp = allow_search_by_ipp
        self.right_read_opposed_patients_data = allow_read_opposed_patient
        if read_nomi:
            self.read_role = "READ_PATIENT_NOMINATIVE"
        elif read_pseudo:
            self.read_role = "READ_PATIENT_PSEUDO_ANONYMIZE"
        else:
            self.read_role = "NO READ PATIENT RIGHT"


def get_perimeters_read_rights(target_perimeters: QuerySet,
                               top_read_nomi_perimeters_ids: List[int],
                               top_read_pseudo_perimeters_ids: List[int],
                               allow_search_by_ipp: bool,
                               allow_read_opposed_patient: bool) -> List[PerimeterReadRight]:
    perimeter_read_right_list = []

    if not (top_read_nomi_perimeters_ids or top_read_pseudo_perimeters_ids):
        return perimeter_read_right_list

    for perimeter in target_perimeters:
        perimeter_and_parents_ids = [perimeter.id] + perimeter.above_levels
        read_nomi, read_pseudo = False, False
        if any(perimeter_id in top_read_nomi_perimeters_ids for perimeter_id in perimeter_and_parents_ids):
            read_nomi, read_pseudo = True, True
        elif any(perimeter_id in top_read_pseudo_perimeters_ids for perimeter_id in perimeter_and_parents_ids):
            read_pseudo = True
        perimeter_read_right_list.append(PerimeterReadRight(perimeter=perimeter,
                                                            read_nomi=read_nomi,
                                                            read_pseudo=read_pseudo,
                                                            allow_search_by_ipp=allow_search_by_ipp,
                                                            allow_read_opposed_patient=allow_read_opposed_patient))
    return perimeter_read_right_list


def get_top_perimeters_with_right_read_nomi(read_nomi_perimeters_ids: List[int]) -> List[int]:
    """ for each perimeter with nominative read right, remove it if any of its parents has nomi access """
    for perimeter in Perimeter.objects.filter(id__in=read_nomi_perimeters_ids):
        if any(parent_id in read_nomi_perimeters_ids for parent_id in perimeter.above_levels):
            try:
                read_nomi_perimeters_ids.remove(perimeter.id)
            except ValueError:
                continue
    return read_nomi_perimeters_ids


def get_top_perimeters_with_right_read_pseudo(top_read_nomi_perimeters_ids: List[int],
                                              read_pseudo_perimeters_ids: List[int]) -> List[int]:
    """ for each perimeter with pseudo read right, remove it if it has nomi access too or if any of its parents has nomi or pseudo access """
    for perimeter in Perimeter.objects.filter(id__in=read_pseudo_perimeters_ids):
        if any((parent_id in read_pseudo_perimeters_ids
                or parent_id in top_read_nomi_perimeters_ids
                or perimeter.id in top_read_nomi_perimeters_ids) for parent_id in perimeter.above_levels):
            try:
                read_pseudo_perimeters_ids.remove(perimeter.id)
            except ValueError:
                continue
    return read_pseudo_perimeters_ids


def get_data_reading_rights_on_perimeters(user: User, target_perimeters: QuerySet):
    user_accesses = get_user_valid_manual_accesses(user=user)
    read_patient_nominative_accesses = user_accesses.filter(Role.q_allow_read_patient_data_nominative())
    read_patient_pseudo_accesses = user_accesses.filter(Role.q_allow_read_patient_data_pseudo() |
                                                        Role.q_allow_read_patient_data_nominative())
    allow_search_by_ipp = user_accesses.filter(Role.q_allow_search_patients_by_ipp()).exists()
    allow_read_opposed_patient = user_accesses.filter(Role.q_allow_read_research_opposed_patient_data()).exists()

    read_nomi_perimeters_ids = [access.perimeter_id for access in read_patient_nominative_accesses]
    read_pseudo_perimeters_ids = [access.perimeter_id for access in read_patient_pseudo_accesses]

    top_read_nomi_perimeters_ids = get_top_perimeters_with_right_read_nomi(read_nomi_perimeters_ids=read_nomi_perimeters_ids)
    top_read_pseudo_perimeters_ids = get_top_perimeters_with_right_read_pseudo(top_read_nomi_perimeters_ids=top_read_nomi_perimeters_ids,
                                                                               read_pseudo_perimeters_ids=read_pseudo_perimeters_ids)

    perimeters_read_rights = get_perimeters_read_rights(target_perimeters=target_perimeters,
                                                        top_read_nomi_perimeters_ids=top_read_nomi_perimeters_ids,
                                                        top_read_pseudo_perimeters_ids=top_read_pseudo_perimeters_ids,
                                                        allow_search_by_ipp=allow_search_by_ipp,
                                                        allow_read_opposed_patient=allow_read_opposed_patient)
    return perimeters_read_rights


def get_target_perimeters(cohort_ids: str, owner: User) -> QuerySet:
    virtual_cohort_ids = get_list_cohort_id_care_site(cohorts_ids=[int(cohort_id) for cohort_id in cohort_ids.split(",")],
                                                      all_user_cohorts=owner.user_cohorts.all())
    return Perimeter.objects.filter(cohort_id__in=virtual_cohort_ids)


def has_at_least_one_read_nominative_access(target_perimeters: QuerySet, nomi_perimeters_ids: List[int]) -> bool:
    for perimeter in target_perimeters:
        perimeter_and_parents_ids = [perimeter.id] + perimeter.above_levels
        if any(p_id in nomi_perimeters_ids for p_id in perimeter_and_parents_ids):
            return True
    return False


def check_user_can_read_patient_data_in_nomi(user: User, target_perimeters: QuerySet) -> bool:
    user_accesses = get_user_valid_manual_accesses(user=user)
    read_patient_data_nomi_accesses = user_accesses.filter(Role.q_allow_read_patient_data_nominative())

    nomi_perimeters_ids = [access.perimeter_id for access in read_patient_data_nomi_accesses]
    allow_read_patient_data_nomi = has_at_least_one_read_nominative_access(target_perimeters=target_perimeters,
                                                                           nomi_perimeters_ids=nomi_perimeters_ids)
    return allow_read_patient_data_nomi


def user_has_at_least_one_pseudo_access_on_target_perimeters(target_perimeters: QuerySet,
                                                             nomi_perimeters_ids: List[int],
                                                             pseudo_perimeters_ids: List[int]) -> bool:
    for perimeter in target_perimeters:
        perimeter_and_parents_ids = [perimeter.id] + perimeter.above_levels
        if any(p_id in pseudo_perimeters_ids and p_id not in nomi_perimeters_ids for p_id in perimeter_and_parents_ids):
            return True


def user_has_at_least_one_pseudo_access(nomi_perimeters_ids: List[int], pseudo_perimeters_ids: List[int]) -> bool:
    for perimeter in Perimeter.objects.filter(id__in=pseudo_perimeters_ids):
        perimeter_and_parents_ids = [perimeter.id] + perimeter.above_levels
        if all(p_id not in nomi_perimeters_ids for p_id in perimeter_and_parents_ids):
            return True
    return False


def check_user_can_read_patient_data_in_pseudo(user: User, target_perimeters: QuerySet) -> bool:
    user_accesses = get_user_valid_manual_accesses(user=user)
    read_patient_data_nomi_accesses = user_accesses.filter(Role.q_allow_read_patient_data_nominative())
    read_patient_data_pseudo_accesses = user_accesses.filter(Role.q_allow_read_patient_data_pseudo() |
                                                             Role.q_allow_read_patient_data_nominative())

    nomi_perimeters_ids = [access.perimeter_id for access in read_patient_data_nomi_accesses]
    pseudo_perimeters_ids = [access.perimeter_id for access in read_patient_data_pseudo_accesses]

    if target_perimeters:
        allow_read_patient_data_pseudo = user_has_at_least_one_pseudo_access_on_target_perimeters(target_perimeters=target_perimeters,
                                                                                                  nomi_perimeters_ids=nomi_perimeters_ids,
                                                                                                  pseudo_perimeters_ids=pseudo_perimeters_ids)
    else:
        allow_read_patient_data_pseudo = user_has_at_least_one_pseudo_access(nomi_perimeters_ids=nomi_perimeters_ids,
                                                                             pseudo_perimeters_ids=pseudo_perimeters_ids)
    return allow_read_patient_data_pseudo


def check_user_can_read_opposed_patient_data(user: User) -> bool:
    user_accesses = get_user_valid_manual_accesses(user=user)
    return user_accesses.filter(Role.q_allow_read_research_opposed_patient_data()) \
                        .exists()
