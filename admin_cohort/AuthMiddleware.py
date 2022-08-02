import json

from django.http import StreamingHttpResponse, FileResponse
from django.utils.deprecation import MiddlewareMixin


from admin_cohort.models import get_or_create_user_with_info
from rest_framework.authentication import BaseAuthentication

from admin_cohort import conf_auth
from admin_cohort.settings import JWT_SESSION_COOKIE, JWT_REFRESH_COOKIE
from admin_cohort.models import get_or_create_user


class CustomAuthentication(BaseAuthentication):
    def authenticate(self, request):
        auth_method = None
        if getattr(request, "jwt_session_key", None) is not None:
            raw_token = request.jwt_session_key
        else:

            raw_token, auth_method = conf_auth.get_token_from_headers(request)
            if raw_token is None:
                return None

            if type(raw_token) == bytes:
                raw_token = raw_token.decode('utf-8')

            if type(auth_method) == bytes:
                auth_method = auth_method.decode('utf-8')

        try:
            user_info = conf_auth.verify_jwt(raw_token, auth_method)
        except ValueError:
            return None

        if user_info is not None:
            user = get_or_create_user_with_info(user_info)
        else:
            user = get_or_create_user(jwt_access_token=raw_token)
        return user, raw_token


class CustomJwtSessionMiddleware(MiddlewareMixin):
    def process_request(self, request):
        session_key = request.COOKIES.get(JWT_SESSION_COOKIE)
        request.jwt_session_key = session_key
        refresh_key = request.COOKIES.get(JWT_REFRESH_COOKIE)
        request.jwt_refresh_key = refresh_key

    def process_response(self, request, response):
        if request.path.startswith("/accounts/logout"):
            response.delete_cookie(JWT_SESSION_COOKIE)
            response.delete_cookie(JWT_REFRESH_COOKIE)
            return response
        session_key = request.jwt_session_key
        refresh_key = request.jwt_refresh_key

        resp_data = dict()
        if not isinstance(response, StreamingHttpResponse) \
                and not isinstance(response, FileResponse):
            try:
                resp_data = json.loads(response.content)
            except json.JSONDecodeError:
                pass

        # see in admin_cohort.views.CustomLoginView.form_valid
        if 'jwt' in resp_data:
            session_key = resp_data.get('jwt', {}).get('access')
            refresh_key = resp_data.get('jwt', {}).get('refresh')
        else:
            if JWT_SESSION_COOKIE in resp_data:
                session_key = resp_data[JWT_SESSION_COOKIE]
            if JWT_REFRESH_COOKIE in resp_data:
                refresh_key = resp_data[JWT_REFRESH_COOKIE]

        if session_key is not None:
            response.set_cookie(JWT_SESSION_COOKIE, session_key)
        if refresh_key is not None:
            response.set_cookie(JWT_REFRESH_COOKIE, refresh_key)
        return response
