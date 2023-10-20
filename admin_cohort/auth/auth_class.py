from jwt import InvalidTokenError
from rest_framework.authentication import BaseAuthentication

from admin_cohort.auth.utils import get_userinfo_from_token, get_auth_data
from admin_cohort.models import User
from admin_cohort.settings import JWT_AUTH_MODE


class Authentication(BaseAuthentication):
    def authenticate(self, request):
        access_token, auth_method = get_auth_data(request)
        if access_token is None:
            return None
        auth_method = auth_method or JWT_AUTH_MODE
        if isinstance(access_token, bytes):
            access_token = access_token.decode('utf-8')
        if isinstance(auth_method, bytes):
            auth_method = auth_method.decode('utf-8')
        try:
            user_info = get_userinfo_from_token(token=access_token, auth_method=auth_method)
            user = User.objects.get(provider_username=user_info.username)
        except (InvalidTokenError, ValueError, User.DoesNotExist):
            return None
        return user, access_token
