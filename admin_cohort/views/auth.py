from django.contrib.auth import login
from django.contrib.auth.views import LoginView
from django.http import JsonResponse, HttpResponseRedirect, Http404
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from environ import environ
from rest_framework import viewsets, status
from rest_framework.response import Response

from accesses.models import Profile, Access
from accesses.serializers import AccessSerializer
from admin_cohort.auth import auth_utils
from admin_cohort.auth.auth_form import AuthForm
from admin_cohort.models import User
from admin_cohort.serializers import UserSerializer
from admin_cohort.settings import MANUAL_SOURCE

env = environ.Env()

OIDC_SERVER_URL = env("OIDC_SERVER_URL")
OIDC_SERVER_AUTH = f"{OIDC_SERVER_URL}/protocol/openid-connect/token"

CLIENT_ID = env("CLIENT_ID")
CLIENT_SECRET = env("CLIENT_SECRET")
GRANT_TYPE = env("GRANT_TYPE")
REDIRECT_URI = env("REDIRECT_URI")


class OIDCTokensView(viewsets.GenericViewSet):
    authentication_classes = []
    permission_classes = []

    @method_decorator(csrf_exempt)
    @method_decorator(never_cache)
    def post(self, request, *args, **kwargs):
        code = request.data.get("code")
        if not code:
            return Response(data={"error": "OIDC Authorization Code not provided"}, status=status.HTTP_400_BAD_REQUEST)

        user, access_token, refresh_token = auth_utils.get_oidc_tokens(code=code)
        user_valid_profiles_ids = [p.id for p in Profile.objects.filter(user_id=user.provider_username,
                                                                        source=MANUAL_SOURCE) if p.is_valid]
        valid_accesses = [a for a in Access.objects.filter(profile_id__in=user_valid_profiles_ids) if a.is_valid]
        accesses = AccessSerializer(valid_accesses, many=True).data
        user = UserSerializer(user).data
        data = {"provider": user,
                "user": user,
                "session_id": self.request.session.session_key,
                "accesses": accesses,
                "jwt": {"access": access_token,
                        "refresh": refresh_token,
                        "last_connection": getattr(self.request, 'last_connection', dict())
                        }
                }
        return Response(data=data, status=status.HTTP_200_OK)


class CustomLoginView(LoginView):
    form_class = AuthForm

    def form_valid(self, form):
        login(self.request, form.get_user())
        u = User.objects.get(provider_username=self.request.user.provider_username)
        user_valid_profiles_ids = [p.id for p in Profile.objects.filter(user_id=u.provider_username,
                                                                        source=MANUAL_SOURCE) if p.is_valid]
        # TODO for RESt API: being returned with users/:user_id/accesses
        valid_accesses = [a for a in Access.objects.filter(profile_id__in=user_valid_profiles_ids) if a.is_valid]
        accesses = AccessSerializer(valid_accesses, many=True).data
        user = UserSerializer(u).data
        data = {"provider": user,
                "user": user,
                "session_id": self.request.session.session_key,
                "accesses": accesses,
                "jwt": {"access": self.request.jwt_access_key,
                        "refresh": self.request.jwt_refresh_key,
                        "last_connection": getattr(self.request, 'last_connection', dict())
                        }
                }
        # when ready, try removing jwt field (so that does not process it,
        # because it should be done with cookies only)
        # data = dict(provider=provider,
        # session_id=self.request.session.session_key, accesses=accesses)
        url = self.get_redirect_url()
        return JsonResponse(data) if not url else HttpResponseRedirect(url)

    def form_invalid(self, form):
        return JsonResponse(data={"errors": form.errors.get('__all__')},
                            status=status.HTTP_401_UNAUTHORIZED)

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


@csrf_exempt
def redirect_token_refresh_view(request):
    if request.method != "POST":
        raise Http404()
    try:
        res = auth_utils.refresh_jwt(request.jwt_refresh_key)
    except ValueError as e:
        raise Http404(e)
    return JsonResponse(data=res.__dict__)
