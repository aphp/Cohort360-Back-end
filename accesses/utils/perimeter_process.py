from typing import List

from django.db.models import QuerySet
from django.http import Http404
from rest_framework.exceptions import ValidationError

from accesses.models import Perimeter, Role
from accesses.tools import get_user_valid_manual_accesses
from admin_cohort.models import User
from cohort.models import CohortResult
from cohort.tools import get_list_cohort_id_care_site


class PerimeterReadRight:
    def __init__(self,
                 perimeter: Perimeter,
                 read_nomi: bool = False,
                 read_pseudo: bool = False,
                 search_by_ipp: bool = False,
                 read_opposed_patients_data: bool = False):
        self.perimeter = perimeter
        self.right_read_patient_nominative = read_nomi
        self.right_read_patient_pseudonymized = read_pseudo
        self.right_search_patients_by_ipp = search_by_ipp
        self.right_read_opposed_patients_data = read_opposed_patients_data
        if read_nomi:
            self.read_role = "READ_PATIENT_NOMINATIVE"
        elif read_pseudo:
            self.read_role = "READ_PATIENT_PSEUDO_ANONYMIZE"
        else:
            self.read_role = "NO READ PATIENT RIGHT"


def get_perimeters_read_rights(target_perimeters: QuerySet,
                               top_read_nomi_perimeters_ids: List[int],
                               top_read_pseudo_perimeters_ids: List[int],
                               search_by_ipp_perimeters_ids: List[int]) -> List[PerimeterReadRight]:
    perimeter_read_right_list = []

    if not (top_read_nomi_perimeters_ids or top_read_pseudo_perimeters_ids):
        return perimeter_read_right_list

    for perimeter in target_perimeters:
        perimeter_and_parents_ids = [perimeter.id] + perimeter.above_levels
        read_nomi, read_pseudo, search_by_ipp = False, False, False
        if any(perimeter_id in top_read_nomi_perimeters_ids for perimeter_id in perimeter_and_parents_ids):
            read_nomi, read_pseudo = True, True
        elif any(perimeter_id in top_read_pseudo_perimeters_ids for perimeter_id in perimeter_and_parents_ids):
            read_pseudo = True
        # todo: remove this if `right_search_patients_by_ipp` is to be global right
        if any(perimeter_id in search_by_ipp_perimeters_ids for perimeter_id in perimeter_and_parents_ids):
            search_by_ipp = True
        # todo: add read_opposed_patient related logic
        # if any(perimeter_id in read_opposed_perimeters_ids for perimeter_id in perimeter_and_parents_ids):
        #     read_opposed_patients_data = True
        perimeter_read_right_list.append(PerimeterReadRight(perimeter=perimeter,
                                                            read_nomi=read_nomi,
                                                            read_pseudo=read_pseudo,
                                                            search_by_ipp=search_by_ipp))
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
    search_by_ipp_accesses = user_accesses.filter(Role.q_allow_search_patients_by_ipp())
    # todo: add   read_opposed_patient_accesses = user_accesses.filter(Role.q_allow_read_research_opposed_patient_data())

    read_nomi_perimeters_ids = [access.perimeter_id for access in read_patient_nominative_accesses]
    read_pseudo_perimeters_ids = [access.perimeter_id for access in read_patient_pseudo_accesses]
    search_by_ipp_perimeters_ids = [access.perimeter_id for access in search_by_ipp_accesses]

    top_read_nomi_perimeters_ids = get_top_perimeters_with_right_read_nomi(read_nomi_perimeters_ids=read_nomi_perimeters_ids)
    top_read_pseudo_perimeters_ids = get_top_perimeters_with_right_read_pseudo(top_read_nomi_perimeters_ids=top_read_nomi_perimeters_ids,
                                                                               read_pseudo_perimeters_ids=read_pseudo_perimeters_ids)

    perimeters_read_rights = get_perimeters_read_rights(target_perimeters=target_perimeters,
                                                        top_read_nomi_perimeters_ids=top_read_nomi_perimeters_ids,
                                                        top_read_pseudo_perimeters_ids=top_read_pseudo_perimeters_ids,
                                                        search_by_ipp_perimeters_ids=search_by_ipp_perimeters_ids)
    return perimeters_read_rights


def get_read_patient_right(perimeters_filtered_by_search, all_read_patient_nominative_accesses,
                           all_read_patient_pseudo_accesses):
    """
    for each search perimeter check of there is at least one access with read right:
    3 response :
    - if no right on one perimeter it raises an error
    - if all perimeters are in nominative return is_pseudo at False
    - else: return is_pseudo at True
    """
    is_pseudo = False
    if not perimeters_filtered_by_search:
        raise ValidationError("No perimeters in parameter for rights verification")
    for perimeter in perimeters_filtered_by_search:
        above_levels_ids = perimeter.above_levels
        above_levels_ids.append(perimeter.id)
        if all_read_patient_nominative_accesses.filter(perimeter_id__in=above_levels_ids):
            continue
        elif all_read_patient_pseudo_accesses.filter(perimeter_id__in=above_levels_ids):
            is_pseudo = True
        else:
            raise ValidationError(f"No read patient role on perimeter {perimeter.id} - {perimeter.name}")
    return not is_pseudo


def get_perimeters_filtered_by_search(cohort_ids, owner_id, default_perimeters):
    """
        Get for any cohort id type (Care_site, Provider) Perimeters from the cohort source population.
    """
    if cohort_ids:
        all_user_cohorts = CohortResult.objects.filter(owner=owner_id)
        list_perimeter_cohort_ids = get_list_cohort_id_care_site(
            [int(cohort_id) for cohort_id in cohort_ids.split(",")], all_user_cohorts)
        return Perimeter.objects.filter(cohort_id__in=list_perimeter_cohort_ids)
    else:
        return default_perimeters


def get_read_nominative_boolean_from_specific_logic_function(request, filter_queryset,
                                                             all_read_patient_nominative_accesses,
                                                             all_read_patient_pseudo_accesses,
                                                             right_perimeter_compute_function) -> bool:
    """
        It takes in input users acesses with read patient right, the initial request  and the specific function to
        apply to find global read patient right on perimeters or cohorts.
        The right_perimeter_compute_function can be used to find right for all cohorts in "is-read-patient-pseudo" or
        at least on one perimeter in "is-one-read-patient-right"
    """

    perimeters_filtered_by_search = get_perimeters_filtered_by_search(request.query_params.get("cohort_id"),
                                                                      request.user, filter_queryset)
    if not perimeters_filtered_by_search:
        raise Http404("ERROR No Perimeters Found")
    return right_perimeter_compute_function(perimeters_filtered_by_search,
                                            all_read_patient_nominative_accesses,
                                            all_read_patient_pseudo_accesses)


def get_all_read_patient_accesses(user) -> tuple:
    """
        Return a tuple of accesses QuerySet, one with read patient nominative role right at True and the other with
        read patient pseudo only at True
        If both are empty there is an issue with user right, it will raise an error
    """
    user_accesses = get_user_valid_manual_accesses(user)
    all_read_patient_nominative_accesses = user_accesses.filter(Role.q_allow_read_patient_data_nominative())
    all_read_patient_pseudo_accesses = user_accesses.filter(Role.q_allow_read_patient_data_pseudo() |
                                                            Role.q_allow_read_patient_data_nominative())
    if not all_read_patient_nominative_accesses and not all_read_patient_pseudo_accesses:
        raise Http404("ERROR No accesses with read patient right Found")
    return all_read_patient_nominative_accesses, all_read_patient_pseudo_accesses


def get_read_opposing_patient_accesses(user) -> bool:
    """
        Return a boolean of accesses opposing patient. It is a global role, so if we found it at least on one care_site
        it will be effective for every perimeters
    """
    user_accesses = get_user_valid_manual_accesses(user)
    opposing_patient_accesses = user_accesses.filter(Role.q_allow_read_research_opposed_patient_data())
    return opposing_patient_accesses.exists()


def has_at_least_one_read_nominative_right(perimeters_filtered_by_search, all_read_patient_nominative_accesses,
                                           all_read_patient_pseudo_accesses):
    """_
    Loop in perimeters, if we found at least one read patient right at Nominative it will return True.
    If there is at least on pseudo and no nominative it will return False.
    Else if there are no rights
    """
    is_pseudo = False
    if not perimeters_filtered_by_search:
        raise ValidationError(
            "ERROR"
            "|perimeter_process.py get_read_patient_right()"
            "|No perimeters in parameter for rights verification")
    for perimeter in perimeters_filtered_by_search:
        above_levels_ids = perimeter.above_levels
        above_levels_ids.append(perimeter.id)
        if all_read_patient_nominative_accesses.filter(perimeter_id__in=above_levels_ids):
            return True
        elif all_read_patient_pseudo_accesses.filter(perimeter_id__in=above_levels_ids):
            is_pseudo = True

    if not is_pseudo:
        raise ValidationError(f"ERROR - No read right found on perimeters:  {perimeters_filtered_by_search}")
    return False


def is_pseudo_perimeter_in_top_perimeter(all_read_patient_nominative_accesses, all_read_patient_pseudo_accesses):
    """
    if there is at least one pseudo access with perimeter in top hierarchy return pseudo, if no accesses rise error
    else return Nomi
    """
    nominative_perimeters = [access.perimeter_id for access in all_read_patient_nominative_accesses]
    for access in all_read_patient_pseudo_accesses:
        above_levels_ids = access.perimeter.above_levels
        above_levels_ids.append(access.perimeter_id)
        if not [pseudo_perimeter for pseudo_perimeter in above_levels_ids if pseudo_perimeter in nominative_perimeters]:
            return True
    return False
