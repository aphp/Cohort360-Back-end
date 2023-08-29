import json

from django.conf.global_settings import CSRF_COOKIE_NAME
from django.http import StreamingHttpResponse, FileResponse
from django.utils.deprecation import MiddlewareMixin

from admin_cohort.settings import JWT_ACCESS_COOKIE, JWT_REFRESH_COOKIE, SESSION_COOKIE_NAME, JWT_ACCESS_COOKIE_SECURE, JWT_REFRESH_COOKIE_SECURE


class JWTSessionMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request.jwt_access_key = request.COOKIES.get(JWT_ACCESS_COOKIE)
        request.jwt_refresh_key = request.COOKIES.get(JWT_REFRESH_COOKIE)
        request.META['HTTP_SESSION_ID'] = request.COOKIES.get(SESSION_COOKIE_NAME)

    def process_response(self, request, response):
        if request.path.startswith("/accounts/logout"):
            for cookie in (JWT_ACCESS_COOKIE, JWT_REFRESH_COOKIE, CSRF_COOKIE_NAME):
                response.delete_cookie(cookie)
            return response

        access_key = request.jwt_access_key
        refresh_key = request.jwt_refresh_key
        resp_data = dict()
        if not isinstance(response, (StreamingHttpResponse, FileResponse)):
            try:
                resp_data = json.loads(response.content)
            except json.JSONDecodeError:
                pass

        if 'jwt' in resp_data:                                      # jwt tokens sent as login response
            access_key = resp_data.get('jwt', {}).get('access')
            refresh_key = resp_data.get('jwt', {}).get('refresh')
        else:                                                       # jwt tokens sent as response to refresh
            if JWT_ACCESS_COOKIE in resp_data:
                access_key = resp_data[JWT_ACCESS_COOKIE]
            if JWT_REFRESH_COOKIE in resp_data:
                refresh_key = resp_data[JWT_REFRESH_COOKIE]

        if access_key:
            response.set_cookie(key=JWT_ACCESS_COOKIE, value=access_key, secure=JWT_ACCESS_COOKIE_SECURE)
        if refresh_key:
            response.set_cookie(key=JWT_REFRESH_COOKIE, value=refresh_key, secure=JWT_REFRESH_COOKIE_SECURE)
        return response
