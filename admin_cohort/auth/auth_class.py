from rest_framework.authentication import BaseAuthentication

from admin_cohort.services.auth import auth_service


class Authentication(BaseAuthentication):

    def authenticate(self, request):
        return auth_service.authenticate_request(request)
