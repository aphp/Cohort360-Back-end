import logging
from typing import Union

from admin_cohort import conf_auth
from admin_cohort.conf_auth import LoginError, ServerError, JwtTokens
from admin_cohort.models import User

_logger = logging.getLogger('django.request')


class AuthBackend:

    def authenticate(self, request, username, password):
        try:
            tokens: JwtTokens = conf_auth.check_ids(username=username, password=password)
        except LoginError:
            return
        except ServerError as e:
            request.jwt_server_unavailable = True
            request.jwt_server_message = str(e)
            return
        try:
            user = User.objects.get(provider_username=username)
        except User.DoesNotExist:
            _logger.error(f"The user with id_aph [{username}] has logged in but no associated user account was found in DB")
            return

        request.jwt_session_key = tokens.access
        request.jwt_refresh_key = tokens.refresh
        request.last_connection = tokens.last_connection
        return user

    def get_user(self, user_id) -> Union[User, None]:
        try:
            return User.objects.get(provider_username=user_id)
        except User.DoesNotExist:
            return None
