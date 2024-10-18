import json
import logging
import struct
import traceback
from logging.handlers import SocketHandler

from django.conf import settings

from admin_cohort.middleware.context_request_middleware import context_request


class RequestHeadersInterceptorFilter(logging.Filter):

    def filter(self, record):
        request = context_request.get()

        if request is not None:
            record.request_metadata = {"user_id": not request.user.is_anonymous and request.user.username,
                                       "impersonating": request.headers.get(settings.IMPERSONATING_HEADER),
                                       "trace_id": request.headers.get(settings.TRACE_ID_HEADER,
                                                                       request.META.get(f"HTTP_{settings.TRACE_ID_HEADER}")),
                                       }
        else:
            record.request_metadata = {}

        return True


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

        trace_id, user_id, impersonating = None, None, None

        request_metadata = d.pop("request_metadata", None)
        if request_metadata is not None:
            trace_id = request_metadata.get("trace_id")
            user_id = request_metadata.get("user_id")
            impersonating = request_metadata.get("impersonating")

        d['trace_id'] = trace_id
        d['user_id'] = user_id
        d['impersonating'] = impersonating
        d['msg'] = record.getMessage()
        d['args'] = None
        d['exc_text'] = traceback.format_exception(*d['exc_info']) if d['exc_info'] else None
        # exc_info is not serializable
        d['exc_info'] = None
        # Issue #25685: delete 'message' if present: redundant with 'msg'
        d.pop('message', None)
        d.pop('request', None)
        s = bytes(json.dumps(d), 'utf-8')
        # s = pickle.dumps(d, 1)
        slen = struct.pack(">L", len(s))
        return slen + s
