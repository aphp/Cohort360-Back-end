import json
from functools import reduce
from operator import or_
from typing import List, Union

from django.db.models import Q
from drf_yasg.inspectors import SwaggerAutoSchema


def prettify_dict(obj: Union[dict, list]) -> str:
    return json.dumps(obj, sort_keys=True, indent=2, default=str)


def prettify_json(str_json: str) -> str:
    try:
        return prettify_dict(json.loads(str_json))
    except Exception:
        return str_json


# seen on https://stackoverflow.com/a/64440802
class CustomAutoSchema(SwaggerAutoSchema):
    def get_tags(self, operation_keys=None):
        tags = self.overrides.get('tags', None) \
               or getattr(self.view, 'swagger_tags', [])
        if not tags:
            tags = [operation_keys[0]]

        return tags
# DJANGO Q HELPER


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
