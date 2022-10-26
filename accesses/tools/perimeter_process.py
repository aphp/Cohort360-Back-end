from accesses.models import Perimeter, Access


def string_to_int_list(str_list: str) -> [int]:
    if len(str_list) == 0:
        print("WARN: string list field empty")
        return []
    try:
        # [:-1] to remove ',' at the end of str
        if (str_list[-1]) == ",":
            return [int(i) for i in str_list[:-1].split(",")]
        else:
            return [int(i) for i in str_list.split(",")]
    except Exception as err:
        raise f"Error in element str list conversion to integer: {err}"


"""
Check for each parent if we found it il perimeters already given in accesses, so if the current perimeter is a child
of another given perimeter.
"""


def is_perimeter_in_top_hierarchy(above_list: [int], all_distinct_perimeters: [Perimeter]) -> bool:
    if above_list is None or above_list == "":
        return True
    is_top = True
    for perimeter in all_distinct_perimeters:
        if perimeter.id in above_list:
            is_top = False
    return is_top


"""
for each perimeter in same level access we get the above perimeter list.
if we find an id in this list one id already present in another access, it is meaning this perimeter is not a top of
roles perimeter hierarchy of user.
if it is, we add current id to the list

We consider a right on a same level equal to right on the current level and all children
"""


def get_top_perimeter_same_level(accesses_same_levels: [Access], all_distinct_perimeters: [Perimeter]) -> [Perimeter]:
    response_list = []
    for access in accesses_same_levels:
        perimeter = access.perimeter
        if perimeter is None:
            pass
        above_list = string_to_int_list(perimeter.above_levels_ids)
        if is_perimeter_in_top_hierarchy(above_list, all_distinct_perimeters):
            response_list.append(perimeter)
    return response_list


"""
for each perimeter in inferior level access we get the above perimeter list.
if we find an id in this list one id already present in another access, it is meaning this perimeter is not a top of
roles perimeter hierarchy of user.
if it is, we add all children perimeter id to the list
"""


def get_top_perimeter_inf_level(accesses_inf_levels: [Access], all_distinct_perimeters: [Perimeter],
                                same_level_perimeters_response: [Perimeter]) -> [Perimeter]:
    response_list = []
    for access in accesses_inf_levels:
        perimeter = access.perimeter
        if perimeter is None:
            pass
        above_list = string_to_int_list(perimeter.above_levels_ids)
        if is_perimeter_in_top_hierarchy(above_list, all_distinct_perimeters) and \
                is_perimeter_in_top_hierarchy([perimeter.id], same_level_perimeters_response):
            if perimeter.bellow_levels_ids is None:
                print("WARN: No lower levels perimeters found! ")
                pass
            children_list = string_to_int_list(perimeter.bellow_levels_ids)
            if len(children_list) == 0:
                pass
            children_perimeters = Perimeter.objects.filter(id__in=children_list)
            for perimeter_child in children_perimeters:
                response_list.append(perimeter_child)
    return response_list
