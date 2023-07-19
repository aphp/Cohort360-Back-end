import json
from _operator import or_
from functools import reduce
from typing import Union, Iterable, List

from django.db.models import Q


def prettify_dict(obj: Union[dict, list]) -> str:
    return json.dumps(obj, sort_keys=True, indent=2, default=str)


def prettify_json(str_json: str) -> str:
    try:
        return prettify_dict(json.loads(str_json))
    except Exception:
        return str_json


def join_qs(qs: Iterable[Q]) -> Q:
    """
    Returns a neutral query that joins, with a OR operator,
    all the results from queries in qs
    @param qs:
    @return:
    """
    lst_qs = list(qs)
    if not len(lst_qs):
        return ~Q()
    return reduce(or_, lst_qs, lst_qs.pop())


def exclude_qs(qs: List[Q]) -> Q:
    """
    Returns a neutral query that exludes all the results from queries in qs
    @param qs:
    @return:
    """
    return Q(*[~q for q in qs])
