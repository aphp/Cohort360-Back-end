import logging

from admin_cohort import conf_auth
from admin_cohort.conf_auth import LoginError, ServerError, JwtTokens
from admin_cohort.models import User, get_or_create_user_with_info

_logger = logging.getLogger('django.request')


def get_or_create_user(jwt_access_token: str) -> User:
    user_info = conf_auth.get_user_info(jwt_access_token=jwt_access_token)
    return get_or_create_user_with_info(user_info)


class AuthBackend:

    def authenticate(self, request, username, password):
        try:
            tokens: JwtTokens = conf_auth.check_ids(username=username,
                                                    password=password)
        except LoginError:
            return
        except ServerError as e:
            request.jwt_server_unavailable = True
            request.jwt_server_message = str(e)
            return

        try:
            user = User.objects.get(provider_username=username)
        except User.DoesNotExist:
            user = get_or_create_user(jwt_access_token=tokens.access)

        request.jwt_session_key = tokens.access
        request.jwt_refresh_key = tokens.refresh
        request.last_connection = tokens.last_connection
        return user

    def get_user(self, user_id) -> User:
        try:
            return User.objects.get(provider_username=user_id)
        except User.DoesNotExist:
            return None
