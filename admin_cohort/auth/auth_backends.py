from admin_cohort.auth.auth_utils import get_jwt_tokens, JwtTokens
from admin_cohort.models import User


class JWTAuthBackend:

    def authenticate(self, request, username, password):
        user = self.get_user(username)
        tokens: JwtTokens = get_jwt_tokens(username=username, password=password)
        request.jwt_access_key = tokens.access
        request.jwt_refresh_key = tokens.refresh
        request.last_connection = tokens.last_connection
        return user

    def get_user(self, user_id) -> User:
        return User.objects.get(provider_username=user_id)
