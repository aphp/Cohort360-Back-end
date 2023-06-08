import json
import logging

from django.http import StreamingHttpResponse, FileResponse
from django.utils.deprecation import MiddlewareMixin
from rest_framework.authentication import BaseAuthentication

from admin_cohort.auth import auth_conf
from admin_cohort.models import User
from admin_cohort.settings import JWT_ACCESS_COOKIE, JWT_REFRESH_COOKIE, SESSION_COOKIE_NAME

_logger = logging.getLogger('django.request')


class CustomAuthentication(BaseAuthentication):
    def authenticate(self, request):
        auth_method = None
        if getattr(request, "jwt_access_key", None) is not None:
            raw_token = request.jwt_access_key
        else:
            raw_token, auth_method = auth_conf.get_token_from_headers(request)
            if raw_token is None:
                return None

            if type(raw_token) == bytes:
                raw_token = raw_token.decode('utf-8')
            if type(auth_method) == bytes:
                auth_method = auth_method.decode('utf-8')
        try:
            user_info = auth_conf.verify_jwt(raw_token, auth_method)
            user = User.objects.get(provider_username=user_info.username)
        except (ValueError, User.DoesNotExist):
            return None
        return user, raw_token


class CustomJwtSessionMiddleware(MiddlewareMixin):
    def process_request(self, request):
        access_key = request.COOKIES.get(JWT_ACCESS_COOKIE)
        request.jwt_access_key = access_key
        refresh_key = request.COOKIES.get(JWT_REFRESH_COOKIE)
        request.jwt_refresh_key = refresh_key
        session_id = request.COOKIES.get(SESSION_COOKIE_NAME)
        request.META['HTTP_SESSION_ID'] = session_id

    def process_response(self, request, response):
        if request.path.startswith("/accounts/logout"):
            response.delete_cookie(JWT_ACCESS_COOKIE)
            response.delete_cookie(JWT_REFRESH_COOKIE)
            return response
        access_key = request.jwt_access_key
        refresh_key = request.jwt_refresh_key

        resp_data = dict()
        if not isinstance(response, (StreamingHttpResponse, FileResponse)):
            try:
                resp_data = json.loads(response.content)
            except json.JSONDecodeError:
                pass

        # see in admin_cohort.views.CustomLoginView.form_valid
        if 'jwt' in resp_data:
            access_key = resp_data.get('jwt', {}).get('access')
            refresh_key = resp_data.get('jwt', {}).get('refresh')
        else:
            if JWT_ACCESS_COOKIE in resp_data:
                access_key = resp_data[JWT_ACCESS_COOKIE]
            if JWT_REFRESH_COOKIE in resp_data:
                refresh_key = resp_data[JWT_REFRESH_COOKIE]

        if access_key is not None:
            response.set_cookie(JWT_ACCESS_COOKIE, access_key)
        if refresh_key is not None:
            response.set_cookie(JWT_REFRESH_COOKIE, refresh_key)
        return response