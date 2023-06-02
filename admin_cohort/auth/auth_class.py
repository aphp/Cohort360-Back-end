from rest_framework.authentication import BaseAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken

from admin_cohort.auth.utils import get_token_from_headers, verify_token
from admin_cohort.models import User


class Authentication(BaseAuthentication):
    def authenticate(self, request):
        if getattr(request, "jwt_access_key", None):
            raw_token = request.jwt_access_key
        else:
            raw_token, _ = get_token_from_headers(request)
            if not raw_token:
                return None
            if type(raw_token) == bytes:
                raw_token = raw_token.decode('utf-8')
        try:
            user_info = verify_token(raw_token)
            user = User.objects.get(provider_username=user_info.username)
        except (InvalidToken, User.DoesNotExist):
            return None
        return user, raw_token
