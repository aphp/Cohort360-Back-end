import json
from enum import Enum
from functools import reduce
from operator import or_
from typing import List, Union, Iterable

from django.conf import settings
from django.db.models import Q
from django.views.debug import SafeExceptionReporterFilter, CLEANSED_SUBSTITUTE


def prettify_dict(obj: Union[dict, list]) -> str:
    return json.dumps(obj, sort_keys=True, indent=2, default=str)


def prettify_json(str_json: str) -> str:
    try:
        return prettify_dict(json.loads(str_json))
    except Exception:
        return str_json


# DJANGO Q HELPERS

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


class StrEnum(str, Enum):
    def __str__(self):
        return self.value

    @classmethod
    def list(cls, exclude: List[str] = None):
        exclude = exclude or [""]
        return [c.value for c in cls if c.value not in exclude]


class CustomExceptionReporterFilter(SafeExceptionReporterFilter):

    def get_post_parameters(self, request):
        immutable_post_params = super(CustomExceptionReporterFilter, self).get_post_parameters(request)
        post_params = immutable_post_params.copy()
        for param_name in settings.CUSTOM_SENSITIVE_POST_PARAMS:
            if param_name in post_params:
                post_params[param_name] = CLEANSED_SUBSTITUTE
        return post_params
