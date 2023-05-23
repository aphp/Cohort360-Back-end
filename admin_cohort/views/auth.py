import requests
from django.contrib.auth import login
from django.contrib.auth.views import LoginView
from django.http import JsonResponse, HttpResponseRedirect, Http404
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from environ import environ
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from accesses.models import Profile, Access
from accesses.serializers import AccessSerializer
from admin_cohort.auth import auth_conf
from admin_cohort.auth.auth_conf import verify_jwt
from admin_cohort.auth.auth_form import AuthForm
from admin_cohort.models import User
from admin_cohort.serializers import UserSerializer
from admin_cohort.settings import MANUAL_SOURCE

env = environ.Env()

OIDC_SERVER_URL = env("OIDC_SERVER_URL")
OIDC_SERVER_AUTH = f"{OIDC_SERVER_URL}/login-actions/authenticate"


class OIDCTokensView(viewsets.GenericViewSet):

    @action(url_path='/', methods=['get'], detail=False)
    def get_oidc_tokens(self, request, *args, **kwargs):
        client_id = request.params.get("client_id")
        client_secret = request.params.get("client_secret")
        grant_type = request.params.get("grant_type")
        code = request.params.get("code")
        redirect_uri = request.params.get("redirect_uri")

        if not all((client_id, client_secret, grant_type, code, redirect_uri)):
            return Response(data={"error": "Request missing one or many OIDC auth params"},
                            status=status.HTTP_400_BAD_REQUEST)

        OIDC_SERVER_AUTH_URL = f"{OIDC_SERVER_AUTH}?client_id={client_id}&" \
                               f"client_secret={client_secret}&" \
                               f"grant_type={grant_type}&" \
                               f"code={code}&" \
                               f"redirect_uri={redirect_uri}"
        response = requests.post(url=OIDC_SERVER_AUTH_URL)
        response = response.json()
        verify_jwt()
        return Response(data={"success": "user logged in"}, status=status.HTTP_200_OK)


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
        res = auth_conf.refresh_jwt(request.jwt_refresh_key)
    except ValueError as e:
        raise Http404(e)
    return JsonResponse(data=res.__dict__)
