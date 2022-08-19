import json
from enum import Enum
from functools import reduce
from operator import or_
from typing import List, Union

from django.db.models import Q


def prettify_dict(obj: Union[dict, list]) -> str:
    return json.dumps(obj, sort_keys=True, indent=2, default=str)


def prettify_json(str_json: str) -> str:
    try:
        return prettify_dict(json.loads(str_json))
    except Exception:
        return str_json


# DJANGO Q HELPERS

def join_qs(qs: List[Q]) -> Q:
    """
    Returns a neutral query that joins, with a OR operator,
    all the results from queries in qs
    @param qs:
    @return:
    """
    if not len(qs):
        return Q()
    return reduce(or_, qs, qs.pop())


def exclude_qs(qs: List[Q]) -> Q:
    """
    Returns a neutral query that exludes all the results from queries in qs
    @param qs:
    @return:
    """
    return Q(*[~q for q in qs])


class StrEnum(str, Enum):
    def __str__(self):
        return self.value

    @classmethod
    def list(cls, exclude: List[str] = None):
        exclude = exclude or [""]
        return [c.value for c in cls if c.value not in exclude]
