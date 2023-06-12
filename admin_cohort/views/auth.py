import logging
from collections import defaultdict

from django.contrib.auth import authenticate, login
from django.contrib.auth import views
from django.http import JsonResponse, HttpResponseRedirect
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from requests import RequestException
from rest_framework import status
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import InvalidToken

from accesses.models import Profile, Access
from accesses.serializers import AccessSerializer
from admin_cohort.auth.utils import logout_user, refresh_oidc_token, refresh_jwt_token
from admin_cohort.auth.auth_form import AuthForm
from admin_cohort.models import User
from admin_cohort.serializers import UserSerializer
from admin_cohort.settings import MANUAL_SOURCE, AUTHENTICATION_BACKENDS
from admin_cohort.types import JwtTokens


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


class OIDCTokensView(View):
    authentication_classes = []
    permission_classes = []

    @method_decorator(csrf_exempt)
    @method_decorator(never_cache)
    def dispatch(self, request, *args, **kwargs):
        return super(OIDCTokensView, self).dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        auth_code = request.POST.get("auth_code")
        if not auth_code:
            return JsonResponse(data={"error": "OIDC Authorization Code not provided"},
                                status=status.HTTP_400_BAD_REQUEST)

        user = authenticate(request=request, code=auth_code)
        login(request=request, user=user, backend=AUTHENTICATION_BACKENDS[1])
        return JsonResponse(data=get_response_data(request=request, user=user),
                            status=status.HTTP_200_OK)


class JWTLoginView(views.LoginView):
    form_class = AuthForm
    http_method_names = ["get", "post", "head", "options"]

    @method_decorator(csrf_exempt)
    @method_decorator(never_cache)
    def dispatch(self, request, *args, **kwargs):
        if self.redirect_authenticated_user and self.request.user.is_authenticated:
            redirect_to = self.get_success_url()
            if redirect_to == self.request.path:
                raise ValueError("Redirection loop for authenticated user detected. "
                                 "Check that your LOGIN_REDIRECT_URL doesn't point to a login page.")
            return HttpResponseRedirect(redirect_to)
        if request.method.lower() in self.http_method_names:
            handler = getattr(self, request.method.lower(), self.http_method_not_allowed)
        else:
            handler = self.http_method_not_allowed
        return handler(request, *args, **kwargs)

    def form_valid(self, form):
        login(self.request, form.get_user())
        data = get_response_data(request=self.request, user=self.request.user)
        url = self.get_redirect_url()
        return JsonResponse(data=data, status=status.HTTP_200_OK) if not url else HttpResponseRedirect(url)

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
    errors = defaultdict(list)
    for refresher in (refresh_jwt_token, refresh_oidc_token):
        try:
            response = refresher(request.jwt_refresh_key)
            if response.status_code == status.HTTP_200_OK:
                tokens = JwtTokens(**response.json())
                return JsonResponse(data=tokens.__dict__, status=status.HTTP_200_OK)
            elif response.status_code == status.HTTP_401_UNAUTHORIZED:
                raise InvalidToken()
            response.raise_for_status()
        except (InvalidToken, RequestException) as e:
            errors[refresher.__name__].append(str(e))

    if errors:
        _logger.error(f"Error while refreshing access token: {errors}")
        return JsonResponse(data={"errors": errors},
                            status=status.HTTP_401_UNAUTHORIZED)
