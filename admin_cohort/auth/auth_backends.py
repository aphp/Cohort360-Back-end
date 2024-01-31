from admin_cohort.auth.utils import get_jwt_tokens, get_oidc_tokens, get_oidc_user_info
from admin_cohort.models import User
from admin_cohort.types import JwtTokens, UserInfo


class BaseAuthBackend:
    def get_user(self, user_id) -> User:
        return User.objects.get(username=user_id)

    def set_tokens_for_request(self, request, tokens: JwtTokens):
        request.jwt_access_key = tokens.access
        request.jwt_refresh_key = tokens.refresh
        request.last_connection = tokens.last_connection


class JWTAuthBackend(BaseAuthBackend):

    def authenticate(self, request, username, password):
        tokens: JwtTokens = get_jwt_tokens(username=username, password=password)
        self.set_tokens_for_request(request=request, tokens=tokens)
        user = self.get_user(username)
        return user


class OIDCAuthBackend(BaseAuthBackend):

    def authenticate(self, request, code):
        tokens: JwtTokens = get_oidc_tokens(code=code)
        self.set_tokens_for_request(request=request, tokens=tokens)
        response = get_oidc_user_info(access_token=tokens.access)
        user_info = UserInfo(**response.json())
        user = self.get_user(user_info.username)
        return user
