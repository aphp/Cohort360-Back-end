from django.http import Http404
from rest_framework.exceptions import ValidationError

from accesses.models import Perimeter, Role
from accesses.tools import get_user_valid_manual_accesses
from accesses.utils.data_right_mapping import PerimeterReadRight
from cohort.models import CohortResult
from cohort.tools import get_list_cohort_id_care_site


def get_right_boolean_for_each_accesses_list(above_levels_ids, all_read_patient_nominative_accesses,
                                             all_read_patient_pseudo_accesses, all_read_ipp_accesses):
    """
    @param above_levels_ids: list of parents perimeters ids
    @param all_read_patient_nominative_accesses:  QuerySet of accesses with nominative read patient right at True
    @param all_read_patient_pseudo_accesses: QuerySet of accesses with nominative read patient right at True or Pseudo
    @param all_read_ipp_accesses: QuerySet of accesses with read IPP right at True
    @return: pseudo, nomi and ipp boolean right for the current perimeter
    """
    nomi, pseudo, ipp = False, False, False
    if all_read_patient_nominative_accesses.filter(perimeter_id__in=above_levels_ids):
        nomi, pseudo = True, True
    elif all_read_patient_pseudo_accesses.filter(perimeter_id__in=above_levels_ids):
        pseudo = True
    if all_read_ipp_accesses.filter(perimeter_id__in=above_levels_ids):
        ipp = True
    return pseudo, nomi, ipp


def filter_accesses_by_search_perimeters(perimeters_filtered_by_search, all_read_patient_nominative_accesses,
                                         all_read_patient_pseudo_accesses, all_read_ipp_accesses) -> list:
    """
    filter Accesses  with perimeters fetch by search params with hierarchy perimeter response and user roles.
    with following rule : Read nominative > Read pseudo
    return dict of perimeter id and tuple of access and perimeter.
    """
    perimeter_read_right_list = []
    for perimeter in perimeters_filtered_by_search:
        above_levels_ids = perimeter.above_levels
        above_levels_ids.append(perimeter.id)
        pseudo, nomi, ipp = get_right_boolean_for_each_accesses_list(above_levels_ids,
                                                                     all_read_patient_nominative_accesses,
                                                                     all_read_patient_pseudo_accesses,
                                                                     all_read_ipp_accesses)
        data_read = PerimeterReadRight(pseudo=pseudo, nomi=nomi, ipp=ipp, perimeter=perimeter)
        perimeter_read_right_list.append(data_read)
    return perimeter_read_right_list


def get_top_perimeter_from_read_patient_accesses(accesses_nomi, accesses_pseudo):
    """
    Get only top hierarchy perimeters with read patient right logical:
    for each perimeters with nominative read right we do not keep perimeter if there is one in the above nomi list
    for each perimeters with pseudo read right we do not keep perimeter if there is one in the above list nomi or pseudo
    or if there nominative at same level.
    @param accesses_nomi:  QuerySet of accesses with nominative read patient right at True
    @param accesses_pseudo: QuerySet of accesses with nominative read patient right at True or Pseudo
    @return: Top perimeters for read patient right
    """
    all_nomi = [access.perimeter.id for access in accesses_nomi]
    all_pseudo = [access.perimeter.id for access in accesses_pseudo]
    for access in accesses_nomi:
        perimeter = access.perimeter
        above_levels_ids = perimeter.above_levels
        for above_perimeter in above_levels_ids:
            if above_perimeter in all_nomi and perimeter.id in all_nomi:
                all_nomi.remove(perimeter.id)
                break
    for access in accesses_pseudo:
        perimeter = access.perimeter
        above_levels_ids = perimeter.above_levels
        for above_perimeter in above_levels_ids:
            if (above_perimeter in all_pseudo or above_perimeter in all_nomi or perimeter.id in all_nomi) \
                    and perimeter.id in all_pseudo:
                all_pseudo.remove(perimeter.id)
                break

    return Perimeter.objects.filter(id__in=set(all_nomi + all_pseudo))


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
