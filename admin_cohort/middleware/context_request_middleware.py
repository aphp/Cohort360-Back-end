import uuid
from contextvars import ContextVar, Token
from typing import Optional, Any, Type

from django.conf import settings
from django.http import HttpRequest

context_request: ContextVar[Optional[HttpRequest]] = ContextVar("context_request", default=None)


class ContextRequestHolder:
    def __init__(self, request: HttpRequest) -> None:
        self.request_token: Optional[Token[Optional[Any]]] = None
        self.request = request

    def __enter__(self) -> Type["ContextRequestHolder"]:
        if settings.TRACE_ID_HEADER not in self.request.headers:
            self.request.META[f"HTTP_{settings.TRACE_ID_HEADER}"] = str(uuid.uuid4())
        self.request_token = context_request.set(self.request)
        return type(self)

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        if self.request_token is not None:
            context_request.reset(self.request_token)


class ContextRequestMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        with ContextRequestHolder(request):
            response = self.get_response(request)
        return response
