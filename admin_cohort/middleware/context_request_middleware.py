import logging
import time
import uuid
from contextvars import ContextVar, Token
from typing import Optional, Any, Type

import environ
from django.conf import settings
from django.http import HttpRequest

env = environ.Env()
logger = logging.getLogger(__name__)

context_request: ContextVar[Optional[HttpRequest]] = ContextVar("context_request", default=None)


def get_trace_id() -> str:
    request = context_request.get()
    if not request:
        return str(uuid.uuid4())
    trace_id_header = settings.TRACE_ID_HEADER
    return request.headers.get(trace_id_header, request.META.get(f"HTTP_{trace_id_header}"))


def get_request_user_id(request) -> str:
    # /!\ local import to avoid Django's loading apps error: AppRegistryNotReady
    from admin_cohort.services.auth import auth_service
    try:
        user_id, _ = auth_service.authenticate_http_request(request)
        return user_id
    except TypeError:
        return "Anonymous"


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
        user_id = get_request_user_id(request)
        trace_id = request.headers.get(settings.TRACE_ID_HEADER, str(uuid.uuid4()))
        impersonating = request.headers.get(settings.IMPERSONATING_HEADER, "-")
        request.environ.update({
            'user_id': user_id,
            'trace_id': trace_id,
            'impersonating': impersonating
        })
        logger.info(f"Request[{trace_id}] {request.method} {request.get_full_path()} | User: {user_id} | Impersonating: {impersonating}")
        with ContextRequestHolder(request):
            start_time = time.perf_counter()
            response = self.get_response(request)
            process_time = f"{time.perf_counter() - start_time:.2f}s"
            response.headers["X-Process-Time"] = process_time
            logger.info(f"Response[{trace_id}] {request.method} {request.get_full_path()} | {response.status_code} | Process-Time: {process_time}")
        return response
