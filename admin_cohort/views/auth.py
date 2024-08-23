import logging

from django.contrib.auth import authenticate, login
from django.contrib.auth import views
from django.http import JsonResponse, HttpResponseRedirect
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from drf_spectacular.utils import extend_schema
from requests import RequestException
from rest_framework import status, viewsets
from rest_framework_simplejwt.exceptions import InvalidToken

from admin_cohort.auth.auth_form import AuthForm
from admin_cohort.models import User
from admin_cohort.serializers import UserSerializer
from admin_cohort.services.auth import auth_service
from admin_cohort.tools.request_log_mixin import RequestLogMixin, JWTLoginRequestLogMixin
from admin_cohort.types import AuthTokens

_logger = logging.getLogger("django.request")


def get_response_data(user: User, auth_tokens: AuthTokens):
    return {"user": UserSerializer(user).data,
            "last_login": user.last_login,
            "access_token": auth_tokens.access_token,
            "refresh_token": auth_tokens.refresh_token
            }


class ExemptedAuthView(View):
    logging_methods = ['POST']

    @method_decorator(csrf_exempt)
    @method_decorator(never_cache)
    def dispatch(self, request, *args, **kwargs):
        if request.method.lower() in self.http_method_names:
            handler = getattr(self, request.method.lower(), self.http_method_not_allowed)
        else:
            handler = self.http_method_not_allowed
        return handler(request, *args, **kwargs)


class OIDCLoginView(RequestLogMixin, viewsets.GenericViewSet):
    permission_classes = []
    http_method_names = ["post"]
    logging_methods = ['POST']

    @extend_schema(exclude=True)
    def post(self, request, *args, **kwargs):
        auth_code = request.data.get("auth_code")
        redirect_uri = request.data.get("redirect_uri")
        if not auth_code:
            return JsonResponse(data={"error": "OIDC Authorization Code not provided"},
                                status=status.HTTP_400_BAD_REQUEST)
        try:
            user = authenticate(request=request, code=auth_code, redirect_uri=redirect_uri)
        except User.DoesNotExist:
            return JsonResponse(data={"error": "User not found in database"},
                                status=status.HTTP_401_UNAUTHORIZED)
        data = get_response_data(user=user, auth_tokens=request.auth_tokens)
        login(request=request, user=user)
        return JsonResponse(data=data, status=status.HTTP_200_OK)


class JWTLoginView(JWTLoginRequestLogMixin, ExemptedAuthView, views.LoginView):
    form_class = AuthForm
    http_method_names = ["post"]

    @method_decorator(csrf_exempt)
    @method_decorator(never_cache)
    def dispatch(self, request, *args, **kwargs):
        super().init_request_log(request)
        response = super().dispatch(request, *args, **kwargs)
        super().finalize_request_log(request)
        return response

    def form_valid(self, form):
        user = form.get_user()
        request = self.request
        data = get_response_data(user=user, auth_tokens=request.auth_tokens)
        login(request, user)
        redirect_url = self.get_redirect_url()
        if redirect_url:
            return HttpResponseRedirect(redirect_url)
        return JsonResponse(data=data, status=status.HTTP_200_OK)

    def form_invalid(self, form):
        return JsonResponse(data={"errors": form.errors.get('__all__')},
                            status=status.HTTP_401_UNAUTHORIZED)


class LogoutView(ExemptedAuthView, views.LogoutView):
    http_method_names = ["post", "get"]

    def post(self, request, *args, **kwargs):
        try:
            auth_service.logout_user(request)
            return JsonResponse(data={}, status=status.HTTP_200_OK)
        except RequestException as e:
            return JsonResponse(data={"error": f"Error on user logout, {e}"}, status=status.HTTP_401_UNAUTHORIZED)


class TokenRefreshView(ExemptedAuthView):
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        try:
            auth_tokens = auth_service.refresh_token(request)
            return JsonResponse(data=auth_tokens, status=status.HTTP_200_OK)
        except (KeyError, InvalidToken, RequestException) as e:
            return JsonResponse(data={"error": f"{e}"}, status=status.HTTP_401_UNAUTHORIZED)


class NotFoundView(View):
    http_method_names = ["get", "post"]

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return JsonResponse(data={"error": "Page Not Found"}, status=status.HTTP_404_NOT_FOUND)
