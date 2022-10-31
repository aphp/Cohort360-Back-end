from accesses.models import Perimeter, Access


def get_perimeters_ids_list(str_ids: str) -> [int]:
    try:
        return [int(i) for i in str_ids.split(",") if i]
    except Exception as err:
        raise f"Error in element str list conversion to integer: {err}"


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
        above_list = get_perimeters_ids_list(perimeter.above_levels_ids)
        if is_perimeter_in_top_hierarchy(above_list, all_distinct_perimeters):
            response_list.append(perimeter)
    return response_list


"""
Check if current access is top read nominative richt accesses perimeter hierarchy,
and return list of top accesses.
"""


def get_top_accesses_nominative(accesses_nominative: [Access], all_nominative_perimeters: [Perimeter]) -> [Access]:
    response_list = []
    for access in accesses_nominative:
        perimeter = access.perimeter
        if perimeter is None:
            pass
        above_list = get_perimeters_ids_list(perimeter.above_levels_ids)
        if is_perimeter_in_top_hierarchy(above_list, all_nominative_perimeters):
            response_list.append(access)
    return response_list


"""
return top of only pseudo read patient right accesses with (read_pseudo: True AND read_nominative:False)
check in first time if pseudo access is top of all pseudo accesses in hierarchy perimeter
In second time, it check if there is no Nominative access in current ou parent perimeter level:
The rule must be => a read nominative right win vs read pseudo right  
A nominative right on one perimeter at True give nominative right for all children of this perimeters.
"""


def get_top_accesses_pseudo(accesses_pseudo: [Access], all_nominative_perimeters: [Perimeter],
                            all_pseudo_perimeters: [Perimeter]) -> [Access]:
    response_list = []
    for access in accesses_pseudo:
        perimeter = access.perimeter
        if perimeter is None:
            pass
        above_list = get_perimeters_ids_list(perimeter.above_levels_ids)
        # if pseudo is top of all pseudo read accesses AND is not child of read nominative accesses
        if is_perimeter_in_top_hierarchy(above_list, all_pseudo_perimeters) and \
                is_perimeter_in_top_hierarchy([perimeter.id] + above_list, all_nominative_perimeters):
            response_list.append(access)
    return response_list


"""
for each perimeter in inferior level access we get the above perimeter list.
if we find an id in this list one id already present in another access, it is meaning this perimeter is not a top of
roles perimeter hierarchy of user.
if it is, we add all children perimeter id to the list
"""


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
        above_list = get_perimeters_ids_list(perimeter.above_levels_ids)
        if is_perimeter_in_top_hierarchy(above_list, all_distinct_perimeters) and \
           is_perimeter_in_top_hierarchy([perimeter.id], same_level_perimeters_response):
            if perimeter.bellow_levels_ids is None:
                print("WARN: No lower levels perimeters found! ")
                pass
            children_list = get_perimeters_ids_list(perimeter.bellow_levels_ids)
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
        above_levels_ids = get_perimeters_ids_list(perimeter.above_levels_ids)
        for top_perimeter in top_hierarchy_perimeter_list:
            if top_perimeter.id == perimeter.id or top_perimeter.id in above_levels_ids:
                response_list.append(perimeter)
    return response_list
