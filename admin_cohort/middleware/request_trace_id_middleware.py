import uuid
from contextvars import ContextVar, Token
from typing import Optional, Any, Type

from django.http import HttpRequest

_request_trace_id: ContextVar[Optional[str]] = ContextVar(
    "_request_id", default=None
)

TRACE_ID_HEADER = "X-Trace-Id"


def add_trace_id(headers: Optional[dict]) -> dict:
    non_null_headers = {} if headers is None else headers
    if TRACE_ID_HEADER not in non_null_headers:
        non_null_headers[TRACE_ID_HEADER] = _request_trace_id.get() or str(uuid.uuid4())
    return non_null_headers


def get_trace_id() -> str:
    return _request_trace_id.get() or str(uuid.uuid4())


class RequestContext:
    def __init__(
        self,
        request: HttpRequest,
    ) -> None:
        self.trace_id_token: Optional[Token[Optional[Any]]] = None
        self.request = request

    def __enter__(self) -> Type["RequestContext"]:
        trace_id = self.request.headers.get("X-Trace-Id") or str(uuid.uuid4())
        self.trace_id_token = _request_trace_id.set(trace_id)
        return type(self)

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        if self.trace_id_token is not None:
            _request_trace_id.reset(self.trace_id_token)


class RequestTraceIdMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        # One-time configuration and initialization.

    def __call__(self, request):
        # Code to be executed for each request before
        # the view (and later middleware) are called.

        with RequestContext(request):
            response = self.get_response(request)

        # Code to be executed for each request/response after
        # the view is called.

        return response
