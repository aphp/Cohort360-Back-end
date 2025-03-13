from django.conf.global_settings import CSRF_COOKIE_NAME
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings


LOGOUT_URL = "/auth/logout/"


class JWTSessionMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request.META['HTTP_SESSION_ID'] = request.COOKIES.get(settings.SESSION_COOKIE_NAME)

    def process_response(self, request, response):
        if request.path.startswith(LOGOUT_URL):
            response.delete_cookie(CSRF_COOKIE_NAME)
        return response
