import json

from django.conf.global_settings import CSRF_COOKIE_NAME
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings


LOGOUT_URL = "/auth/logout/"
REFRESH_URL = "/auth/refresh/"


class JWTSessionMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request.META['HTTP_SESSION_ID'] = request.COOKIES.get(settings.SESSION_COOKIE_NAME)

    def process_response(self, request, response):
        if request.path.startswith(LOGOUT_URL):
            response.delete_cookie(CSRF_COOKIE_NAME)
            response.delete_cookie(settings.ACCESS_TOKEN_COOKIE)
            return response

        access_token = None
        auth_tokens = getattr(request, "auth_tokens", None)
        if auth_tokens:
            access_token = auth_tokens.access_token

        if request.path.startswith(REFRESH_URL):
            try:
                resp_data = json.loads(response.content)
                access_token = resp_data.get(settings.ACCESS_TOKEN_COOKIE)
            except json.JSONDecodeError:
                pass

        if access_token:
            response.set_cookie(key=settings.ACCESS_TOKEN_COOKIE, value=access_token, secure=settings.ACCESS_TOKEN_COOKIE_SECURE)
        return response
