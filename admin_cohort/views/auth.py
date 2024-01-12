import logging

from django.contrib.auth import authenticate, login
from django.contrib.auth import views
from django.http import JsonResponse, HttpResponseRedirect
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from requests import RequestException
from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import InvalidToken

from accesses.models import Profile, Access
from accesses.serializers import AccessSerializer
from admin_cohort.auth.utils import logout_user, refresh_oidc_token, refresh_jwt_token
from admin_cohort.auth.auth_form import AuthForm
from admin_cohort.models import User
from admin_cohort.serializers import UserSerializer
from admin_cohort.settings import MANUAL_SOURCE, OIDC_AUTH_MODE, JWT_AUTH_MODE
from admin_cohort.types import JwtTokens
from admin_cohort.tools.request_log_mixin import RequestLogMixin, JWTLoginRequestLogMixin

_logger = logging.getLogger("django.request")


def get_response_data(request, user: User):
    # TODO for REST API: being returned with users/user_id/accesses
    user_valid_profiles_ids = [p.id for p in Profile.objects.filter(user_id=user.provider_username,
                                                                    source=MANUAL_SOURCE) if p.is_valid]
    valid_accesses = [a for a in Access.objects.filter(profile_id__in=user_valid_profiles_ids) if a.is_valid]
    accesses = AccessSerializer(valid_accesses, many=True).data
    user = UserSerializer(user).data
    data = {"provider": user,
            "user": user,
            "session_id": request.session.session_key,
            "accesses": accesses,
            "jwt": {"access": request.jwt_access_key,
                    "refresh": request.jwt_refresh_key,
                    "last_connection": getattr(request, 'last_connection', dict())
                    }
            }
    # when ready, try removing jwt field (so that does not process it,
    # because it should be done with cookies only)
    return data


class OIDCTokensView(RequestLogMixin, viewsets.ViewSet):
    authentication_classes = []
    permission_classes = []
    logging_methods = ['POST']

    def post(self, request, *args, **kwargs):
        auth_code = request.data.get("auth_code")
        if not auth_code:
            return JsonResponse(data={"error": "OIDC Authorization Code not provided"},
                                status=status.HTTP_400_BAD_REQUEST)

        try:
            user = authenticate(request=request, code=auth_code)
        except User.DoesNotExist:
            return JsonResponse(data={"error": "User not found in database"},
                                status=status.HTTP_401_UNAUTHORIZED)
        login(request=request, user=user)
        return JsonResponse(data=get_response_data(request=request, user=user),
                            status=status.HTTP_200_OK)


class JWTLoginView(JWTLoginRequestLogMixin, views.LoginView):
    form_class = AuthForm
    http_method_names = ["get", "post", "head", "options"]
    logging_methods = ['POST']

    @method_decorator(csrf_exempt)
    @method_decorator(never_cache)
    def dispatch(self, request, *args, **kwargs):
        super().init_request_log(request)
        if request.method.lower() in self.http_method_names:
            handler = getattr(self, request.method.lower(), self.http_method_not_allowed)
        else:
            handler = self.http_method_not_allowed
        response = handler(request, *args, **kwargs)
        super().finalize_request_log(request)
        return response

    def form_valid(self, form):
        login(self.request, form.get_user())
        data = get_response_data(request=self.request, user=self.request.user)
        redirect_url = self.get_redirect_url()
        if redirect_url:
            return HttpResponseRedirect(redirect_url)
        return JsonResponse(data=data, status=status.HTTP_200_OK)

    def form_invalid(self, form):
        return JsonResponse(data={"errors": form.errors.get('__all__')},
                            status=status.HTTP_401_UNAUTHORIZED)


class LogoutView(views.LogoutView):

    @method_decorator(csrf_exempt)
    @method_decorator(never_cache)
    def dispatch(self, request, *args, **kwargs):
        if request.method.lower() in self.http_method_names:
            handler = getattr(self, request.method.lower(), self.http_method_not_allowed)
        else:
            handler = self.http_method_not_allowed
        return handler(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        logout_user(request)
        return JsonResponse(data={}, status=status.HTTP_200_OK)


@csrf_exempt
def token_refresh_view(request):
    if request.method != "POST":
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)
    refreshers = {JWT_AUTH_MODE: refresh_jwt_token,
                  OIDC_AUTH_MODE: refresh_oidc_token
                  }
    try:
        refresher = refreshers[request.META.get("HTTP_AUTHORIZATIONMETHOD")]
        response = refresher(request.jwt_refresh_key)
        if response.status_code == status.HTTP_200_OK:
            tokens = JwtTokens(**response.json())
            return JsonResponse(data=tokens.__dict__, status=status.HTTP_200_OK)
        elif response.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_400_BAD_REQUEST):
            raise InvalidToken("Token is invalid or has expired")
        else:
            response.raise_for_status()
    except KeyError as ke:
        return JsonResponse(data={"error": f"Missing authorization method: {ke}"}, status=status.HTTP_400_BAD_REQUEST)
    except (InvalidToken, RequestException) as e:
        return JsonResponse(data={"error": f"{e}"}, status=status.HTTP_401_UNAUTHORIZED)
