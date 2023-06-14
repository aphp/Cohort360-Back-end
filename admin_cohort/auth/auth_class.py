from rest_framework.authentication import BaseAuthentication

from admin_cohort.auth.utils import get_token_from_headers, verify_token, verify_token_2
from admin_cohort.models import User
from admin_cohort.types import TokenVerificationError


class Authentication(BaseAuthentication):
    def authenticate(self, request):
        auth_method = "JWT"
        if getattr(request, "jwt_access_key", None):
            raw_token = request.jwt_access_key
        else:
            raw_token, auth_method = get_token_from_headers(request)
            if not raw_token:
                return None
            if type(raw_token) == bytes:
                raw_token = raw_token.decode('utf-8')
            if type(auth_method) == bytes:
                auth_method = auth_method.decode('utf-8')
        try:
            # user_info = verify_token(raw_token)
            user_info = verify_token_2(raw_token, auth_method)
            user = User.objects.get(provider_username=user_info.username)
        except (TokenVerificationError, User.DoesNotExist):
            return None
        return user, raw_token
