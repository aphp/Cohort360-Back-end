from rest_framework.authentication import BaseAuthentication

from admin_cohort.auth import auth_utils
from admin_cohort.models import User


class Authentication(BaseAuthentication):
    def authenticate(self, request):
        auth_method = None
        if getattr(request, "jwt_access_key", None) is not None:
            raw_token = request.jwt_access_key
        else:
            raw_token, auth_method = auth_utils.get_token_from_headers(request)
            if raw_token is None:
                return None

            if type(raw_token) == bytes:
                raw_token = raw_token.decode('utf-8')
            if type(auth_method) == bytes:
                auth_method = auth_method.decode('utf-8')
        try:
            user_info = auth_utils.verify_token(raw_token, auth_method)
            user = User.objects.get(provider_username=user_info.username)
        except (ValueError, User.DoesNotExist):
            return None
        return user, raw_token
