from django.contrib.auth import login, logout
from django.contrib.auth import views
from django.contrib.auth.models import update_last_login
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from drf_spectacular.utils import extend_schema
from requests import RequestException
from rest_framework import status, viewsets
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.exceptions import InvalidToken

from admin_cohort.models import User
from admin_cohort.serializers import UserSerializer, LoginFormSerializer, LoginSerializer
from admin_cohort.services.auth import auth_service
from admin_cohort.tools.request_log_mixin import RequestLogMixin
from admin_cohort.types import ServerError


class CSRFExemptedAuthView(View):
    http_method_names = ["post"]

    @method_decorator(csrf_exempt)
    @method_decorator(never_cache)
    def dispatch(self, request, *args, **kwargs):
        if request.method.lower() in self.http_method_names:
            handler = getattr(self, request.method.lower(), self.http_method_not_allowed)
        else:
            handler = self.http_method_not_allowed
        return handler(request, *args, **kwargs)


class LoginView(RequestLogMixin, viewsets.GenericViewSet):
    authentication_classes = []
    permission_classes = []
    http_method_names = ["post"]
    logging_methods = ["POST"]
    swagger_tags = [".Authentication - Login"]

    @extend_schema(tags=swagger_tags,
                   summary="Login with username and password",
                   description="Authenticate user and return an access token.",
                   request=LoginFormSerializer,
                   responses={200: LoginSerializer})
    def post(self, request, *args, **kwargs):
        auth_method = request.META.get('HTTP_AUTHORIZATIONMETHOD')
        try:
            user = auth_service.login(request=request, auth_method=auth_method)
        except (AuthenticationFailed, User.DoesNotExist, ServerError) as e:
            return JsonResponse(data={"error": str(e)}, status=status.HTTP_401_UNAUTHORIZED)
        login(request=request, user=user)
        login_serializer = LoginSerializer(data={"user": UserSerializer(user).data,
                                                 "last_login": user.last_login,
                                                 "access_token": request.auth_tokens.access_token,
                                                 "refresh_token": request.auth_tokens.refresh_token})
        login_serializer.is_valid()
        update_last_login(None, user)
        return JsonResponse(data=login_serializer.data, status=status.HTTP_200_OK)


class LogoutView(CSRFExemptedAuthView, views.LogoutView):

    def post(self, request, *args, **kwargs):
        try:
            auth_service.logout(request)
            logout(request)
            return JsonResponse(data={}, status=status.HTTP_200_OK)
        except RequestException as e:
            return JsonResponse(data={"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TokenRefreshView(CSRFExemptedAuthView, View):

    def post(self, request, *args, **kwargs):
        try:
            auth_tokens = auth_service.refresh_token(request)
            return JsonResponse(data=auth_tokens.__dict__, status=status.HTTP_200_OK)
        except (InvalidToken, ServerError) as e:
            return JsonResponse(data={"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class NotFoundView(View):
    http_method_names = ["get", "post"]

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return JsonResponse(data={"error": "Page Not Found"}, status=status.HTTP_404_NOT_FOUND)
