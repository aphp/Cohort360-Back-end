import json
import struct
from enum import Enum
from functools import reduce
from logging.handlers import SocketHandler
from operator import or_
from typing import List, Union, Iterable

from django.conf import settings
from django.db.models import Q
from django.views.debug import SafeExceptionReporterFilter


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
        for param_name in settings.SENSITIVE_PARAMS:
            if param_name in post_params:
                post_params[param_name] = self.cleansed_substitute
        return post_params

    def get_traceback_frame_variables(self, request, tb_frame):
        cleansed = dict(super(CustomExceptionReporterFilter, self).get_traceback_frame_variables(request, tb_frame))
        for element in cleansed:
            if element in settings.SENSITIVE_PARAMS:
                cleansed[element] = self.cleansed_substitute
        return cleansed.items()


class CustomSocketHandler(SocketHandler):

    def makePickle(self, record):
        """
        Pickles the record in binary format with a length prefix, and
        returns it ready for transmission across the socket.
        """
        record.exc_info and self.format(record)
        # See issue #14436: If msg or args are objects, they may not be
        # available on the receiving end. So we convert the msg % args
        # to a string, save it as msg and zap the args.
        d = dict(record.__dict__)
        d['msg'] = record.getMessage()
        d['args'] = None
        d['exc_info'] = None
        # Issue #25685: delete 'message' if present: redundant with 'msg'
        d.pop('message', None)
        d.pop('request', None)  # as request is not serializable
        s = bytes(json.dumps(d), 'utf-8')
        # s = pickle.dumps(d, 1)
        slen = struct.pack(">L", len(s))
        return slen + s
