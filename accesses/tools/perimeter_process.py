from rest_framework.exceptions import ValidationError

from accesses.models import Perimeter, Access
from accesses.tools.data_right_mapping import PerimeterReadRight
from cohort.models import CohortResult
from cohort.tools import get_list_cohort_id_care_site
from commons.tools import cast_string_to_ids_list


def is_perimeter_in_top_hierarchy(above_list: [int], all_distinct_perimeters: [Perimeter]) -> bool:
    """
    Check for each parent if we found it il perimeters already given in accesses, so if the current perimeter
    is a child of another given perimeter.
    """
    if not above_list:
        return True
    is_top = True
    for perimeter in all_distinct_perimeters:
        if perimeter.id in above_list:
            is_top = False
    return is_top


def get_top_perimeter_same_level(accesses_same_levels: [Access], all_distinct_perimeters: [Perimeter]) -> [Perimeter]:
    """
    for each perimeter in same level access we get the above perimeter list.
    if we find an id in this list one id already present in another access,
    it is meaning this perimeter is not a top of roles perimeter hierarchy of user.
    if it is, we add current id to the list
    We consider a right on a same level equal to right on the current level and all children
    """
    response_list = []
    for access in accesses_same_levels:
        perimeter = access.perimeter
        if perimeter is None:
            pass
        above_list = cast_string_to_ids_list(perimeter.above_levels_ids)
        if is_perimeter_in_top_hierarchy(above_list, all_distinct_perimeters):
            response_list.append(perimeter)
    return response_list


def get_top_perimeter_inf_level(accesses_inf_levels: [Access], all_distinct_perimeters: [Perimeter],
                                same_level_perimeters_response: [Perimeter]) -> [Perimeter]:
    """
    for each perimeter in inferior level access we get the above perimeter list.
    if we find an id in this list one id already present in another access,
    it is meaning this perimeter is not a top of roles perimeter hierarchy of user.
    if it is, we add all children perimeter id to the list
    """
    response_list = []
    for access in accesses_inf_levels:
        perimeter = access.perimeter
        if perimeter is None:
            pass
        above_list = cast_string_to_ids_list(perimeter.above_levels_ids)
        if is_perimeter_in_top_hierarchy(above_list, all_distinct_perimeters) and \
                is_perimeter_in_top_hierarchy([perimeter.id], same_level_perimeters_response):
            if perimeter.inferior_levels_ids is None:
                print("WARN: No lower levels perimeters found! ")
                pass
            children_list = cast_string_to_ids_list(perimeter.inferior_levels_ids)
            if len(children_list) == 0:
                pass
            children_perimeters = Perimeter.objects.filter(id__in=children_list)
            for perimeter_child in children_perimeters:
                response_list.append(perimeter_child)
    return response_list


def filter_perimeter_by_top_hierarchy_perimeter_list(perimeters_filtered_by_search, top_hierarchy_perimeter_list):
    """
    filter the perimeters fetched by search params with hierarchy perimeter response with user Roles and Accesses.
    If there is no search params it return the previous top hierarchy compute response.
    """
    response_list = []
    if not perimeters_filtered_by_search:
        return top_hierarchy_perimeter_list
    for perimeter in perimeters_filtered_by_search:
        above_levels_ids = cast_string_to_ids_list(perimeter.above_levels_ids)
        for top_perimeter in top_hierarchy_perimeter_list:
            if top_perimeter.id == perimeter.id or top_perimeter.id in above_levels_ids:
                response_list.append(perimeter)
    return response_list


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
        above_levels_ids = cast_string_to_ids_list(perimeter.above_levels_ids)
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
        above_levels_ids = cast_string_to_ids_list(perimeter.above_levels_ids)
        for above_perimeter in above_levels_ids:
            if above_perimeter in all_nomi and perimeter.id in all_nomi:
                all_nomi.remove(perimeter.id)
                break
    for access in accesses_pseudo:
        perimeter = access.perimeter
        above_levels_ids = cast_string_to_ids_list(perimeter.above_levels_ids)
        for above_perimeter in above_levels_ids:
            if (above_perimeter in all_pseudo or above_perimeter in all_nomi or perimeter.id in all_nomi) \
                    and perimeter.id in all_pseudo:
                all_pseudo.remove(perimeter.id)
                break

    return Perimeter.objects.filter(id__in=list(set(all_nomi + all_pseudo)))


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
        raise ValidationError(
            "ERROR"
            "|perimeter_process.py get_read_patient_right()"
            "|No perimeters in parameter for rights verification")
    for perimeter in perimeters_filtered_by_search:
        above_levels_ids = cast_string_to_ids_list(perimeter.above_levels_ids)
        above_levels_ids.append(perimeter.id)
        if all_read_patient_nominative_accesses.filter(perimeter_id__in=above_levels_ids):
            pass
        elif all_read_patient_pseudo_accesses.filter(perimeter_id__in=above_levels_ids):
            is_pseudo = True
        else:
            raise ValidationError(
                f"ERROR"
                f"|perimeter_process.py get_read_patient_right()"
                f"|No read patient role on perimeter {perimeter.id} - {perimeter.name}")
    return is_pseudo

def get_perimeters_filtered_by_search(cohort_ids,owner_id, default_perimeters):
    if cohort_ids:
        all_user_cohorts = CohortResult.objects.filter(owner=owner_id)
        list_perimeter_cohort_ids = get_list_cohort_id_care_site(
            [int(cohort_id) for cohort_id in cohort_ids.split(",")], all_user_cohorts)
        return Perimeter.objects.filter(cohort_id__in=list_perimeter_cohort_ids)
    else:
        return default_perimeters
def is_at_least_one_read_Nomitative_right(perimeters_filtered_by_search, all_read_patient_nominative_accesses,
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
        above_levels_ids = cast_string_to_ids_list(perimeter.above_levels_ids)
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
        above_levels_ids = cast_string_to_ids_list(access.perimeter.above_levels_ids)
        above_levels_ids.append(access.perimeter.id)
        if not [pseudo_perimeter for pseudo_perimeter in above_levels_ids if pseudo_perimeter in nominative_perimeters]:
            return True
    return False
