import uuid
from contextvars import ContextVar, Token
from typing import Optional, Any, Type

import jwt
from django.conf import settings
from django.http import HttpRequest


context_request: ContextVar[Optional[HttpRequest]] = ContextVar("context_request", default=None)


def get_trace_id() -> str:
    request = context_request.get()
    if not request:
        return str(uuid.uuid4())
    trace_id_header = settings.TRACE_ID_HEADER
    return request.headers.get(trace_id_header, request.META.get(f"HTTP_{trace_id_header}"))

def get_request_user_id(request) -> str:
    user_id = "Anonymous"
    bearer_token = request.META.get("HTTP_AUTHORIZATION")
    auth_token = bearer_token and bearer_token.split("Bearer ")[1] or None
    if auth_token is not None:
        try:
            decoded = jwt.decode(jwt=auth_token, options={'verify_signature': False})
            user_id = decoded.get("preferred_username", decoded.get("username"))
        except jwt.PyJWTError:
            pass
    return user_id


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
        request.environ.update({
            'user_id': get_request_user_id(request),
            'trace_id': request.headers.get(settings.TRACE_ID_HEADER, str(uuid.uuid4())),
            'impersonating': request.headers.get(settings.IMPERSONATING_HEADER, "-")
        })
        with ContextRequestHolder(request):
            response = self.get_response(request)
        return response
