from typing import Optional

from django.conf import settings

from admin_cohort.services.auth import auth_service
from admin_cohort.models import User
from admin_cohort.types import AuthTokens


class BaseAuthBackend:
    def get_user(self, user_id) -> User:
        return User.objects.get(username=user_id)

    @staticmethod
    def set_auth_tokens(request, auth_tokens: AuthTokens) -> None:
        request.auth_tokens = auth_tokens


class JWTAuthBackend(BaseAuthBackend):

    def authenticate(self, request, username, password):
        auth_tokens = auth_service.get_tokens(username=username, password=password)
        self.set_auth_tokens(request, auth_tokens)
        return self.get_user(username)


class OIDCAuthBackend(BaseAuthBackend):

    def authenticate(self, request, code, redirect_uri: Optional[str] = None):
        auth_tokens = auth_service.get_tokens(code=code, redirect_uri=redirect_uri)
        self.set_auth_tokens(request, auth_tokens)
        username = auth_service.retrieve_username(token=auth_tokens.access_token, auth_method=settings.OIDC_AUTH_MODE)
        return self.get_user(username)
