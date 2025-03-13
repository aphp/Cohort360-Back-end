import logging
from typing import Optional

from rest_framework.exceptions import AuthenticationFailed

from admin_cohort.services.auth import jwt_auth_service, oidc_auth_service
from admin_cohort.models import User


_logger = logging.getLogger("django.request")


class BaseAuthBackend:
    def get_user(self, user_id) -> Optional[User]:
        return User.objects.get(username=user_id)


class JWTAuthBackend(BaseAuthBackend):

    def authenticate(self, request, username, password):
        valid_credentials = jwt_auth_service.check_credentials(username=username, password=password)
        if valid_credentials:
            return self.get_user(user_id=username)
        raise AuthenticationFailed("Invalid username or password!")


class OIDCAuthBackend(BaseAuthBackend):

    def authenticate(self, request, code, redirect_uri: Optional[str] = None):
        auth_tokens = oidc_auth_service.get_tokens(code=code, redirect_uri=redirect_uri)
        if auth_tokens is None:
            raise AuthenticationFailed("Invalid username or password")
        request.auth_tokens = auth_tokens
        username = oidc_auth_service.retrieve_username(token=auth_tokens.access_token)
        return self.get_user(user_id=username)
