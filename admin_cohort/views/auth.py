import json
import logging

from django.contrib.auth import authenticate, login
from django.contrib.auth import views
from django.http import JsonResponse, HttpResponseRedirect
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from requests import RequestException
from rest_framework import status
from rest_framework_simplejwt.exceptions import InvalidToken

from admin_cohort.auth.utils import logout_user, refresh_oidc_token, refresh_jwt_token
from admin_cohort.auth.auth_form import AuthForm
from admin_cohort.models import User
from admin_cohort.serializers import UserSerializer
from admin_cohort.settings import OIDC_AUTH_MODE, JWT_AUTH_MODE
from admin_cohort.types import AuthTokens
from admin_cohort.tools.request_log_mixin import RequestLogMixin, JWTLoginRequestLogMixin

_logger = logging.getLogger("django.request")


def get_response_data(user: User, auth_tokens: AuthTokens):
    return {"user": UserSerializer(user).data,
            "last_login": user.last_login,
            "access_token": auth_tokens.access_token,
            "refresh_token": auth_tokens.refresh_token
            }


class ExemptedAuthView(View):
    http_method_names = ["post"]

    @method_decorator(csrf_exempt)
    @method_decorator(never_cache)
    def dispatch(self, request, *args, **kwargs):
        if request.method.lower() in self.http_method_names:
            handler = getattr(self, request.method.lower(), self.http_method_not_allowed)
        else:
            handler = self.http_method_not_allowed
        return handler(request, *args, **kwargs)


class OIDCLoginView(RequestLogMixin, ExemptedAuthView):
    logging_methods = ['POST']

    def post(self, request, *args, **kwargs):
        auth_code = json.loads(request.body).get("auth_code")
        if not auth_code:
            return JsonResponse(data={"error": "OIDC Authorization Code not provided"},
                                status=status.HTTP_400_BAD_REQUEST)
        try:
            user = authenticate(request=request, code=auth_code)
        except User.DoesNotExist:
            return JsonResponse(data={"error": "User not found in database"},
                                status=status.HTTP_401_UNAUTHORIZED)
        data = get_response_data(user=user, auth_tokens=request.auth_tokens)
        login(request=request, user=user)
        return JsonResponse(data=data, status=status.HTTP_200_OK)


class JWTLoginView(JWTLoginRequestLogMixin, ExemptedAuthView, views.LoginView):
    form_class = AuthForm
    template_name = "login.html"
    http_method_names = ["get", "post"]
    logging_methods = ['POST']

    @method_decorator(csrf_exempt)
    @method_decorator(never_cache)
    def dispatch(self, request, *args, **kwargs):
        super().init_request_log(request)
        response = super().dispatch(request, *args, **kwargs)
        super().finalize_request_log(request)
        return response

    def form_valid(self, form):
        user = form.get_user()
        data = get_response_data(user=user, auth_tokens=self.request.auth_tokens)
        login(self.request, user)
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
            logout_user(request)
        except RequestException as e:
            return JsonResponse(data={"error": f"Error on user logout, {e}"}, status=status.HTTP_401_UNAUTHORIZED)
        return JsonResponse(data={}, status=status.HTTP_200_OK)


class TokenRefreshView(ExemptedAuthView):

    def post(self, request, *args, **kwargs):
        refreshers = {JWT_AUTH_MODE: refresh_jwt_token,
                      OIDC_AUTH_MODE: refresh_oidc_token
                      }
        try:
            refresher = refreshers[request.META.get("HTTP_AUTHORIZATIONMETHOD")]
            refresh_token = json.loads(request.body).get('refresh_token')
            response = refresher(refresh_token)
            if response.status_code == status.HTTP_200_OK:
                return JsonResponse(data=AuthTokens(**response.json()).__dict__,
                                    status=status.HTTP_200_OK)
            elif response.status_code in (status.HTTP_400_BAD_REQUEST, status.HTTP_401_UNAUTHORIZED):
                raise InvalidToken("Token is invalid or has expired")
            else:
                response.raise_for_status()
        except KeyError as ke:
            return JsonResponse(data={"error": f"Missing AUTHORIZATIONMETHOD headers: {ke}"},
                                status=status.HTTP_400_BAD_REQUEST)
        except (InvalidToken, RequestException) as e:
            return JsonResponse(data={"error": f"{e}"},
                                status=status.HTTP_401_UNAUTHORIZED)
