from admin_cohort.auth.utils import get_jwt_tokens, get_oidc_tokens, extract_username_from_token
from admin_cohort.models import User
from admin_cohort.types import AuthTokens


class BaseAuthBackend:
    def get_user(self, user_id) -> User:
        return User.objects.get(username=user_id)

    def set_auth_tokens(self, request, access_tokens: AuthTokens):
        request.auth_tokens = access_tokens


class JWTAuthBackend(BaseAuthBackend):

    def authenticate(self, request, username, password):
        auth_tokens: AuthTokens = get_jwt_tokens(username=username, password=password)
        user = self.get_user(username)
        self.set_auth_tokens(request, auth_tokens)
        return user


class OIDCAuthBackend(BaseAuthBackend):

    def authenticate(self, request, code):
        auth_tokens: AuthTokens = get_oidc_tokens(code=code)
        username = extract_username_from_token(access_token=auth_tokens.access_token)
        user = self.get_user(username)
        self.set_auth_tokens(request, auth_tokens)
        return user
