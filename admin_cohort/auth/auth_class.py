from rest_framework.authentication import BaseAuthentication

from admin_cohort.auth.utils import get_token_from_headers, get_userinfo_from_token
from admin_cohort.models import User
from admin_cohort.types import TokenVerificationError


class Authentication(BaseAuthentication):
    def authenticate(self, request):
        raw_token, auth_method = get_token_from_headers(request)
        if type(raw_token) == bytes:
            raw_token = raw_token.decode('utf-8')
        if type(auth_method) == bytes:
            auth_method = auth_method.decode('utf-8')
        try:
            user_info = get_userinfo_from_token(raw_token, auth_method)
            user = User.objects.get(provider_username=user_info.username)
        except (TokenVerificationError, User.DoesNotExist):
            return None
        return user, raw_token
