from django.contrib.auth import authenticate, logout
from django.contrib.auth.views import LoginView, LogoutView
from django.http import JsonResponse, HttpResponseRedirect
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from rest_framework import viewsets, status
from rest_framework.response import Response

from accesses.models import Profile, Access
from accesses.serializers import AccessSerializer
from admin_cohort.auth.utils import refresh_jwt_token
from admin_cohort.auth.auth_form import AuthForm
from admin_cohort.models import User
from admin_cohort.serializers import UserSerializer
from admin_cohort.settings import MANUAL_SOURCE


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


class OIDCTokensView(viewsets.GenericViewSet):
    authentication_classes = []
    permission_classes = []

    @method_decorator(csrf_exempt)
    @method_decorator(never_cache)
    def post(self, request, *args, **kwargs):
        auth_code = request.data.get("auth_code")
        if not auth_code:
            return Response(data={"error": "OIDC Authorization Code not provided"},
                            status=status.HTTP_400_BAD_REQUEST)

        user = authenticate(request=request, code=auth_code)
        return Response(data=get_response_data(request=request, user=user),
                        status=status.HTTP_200_OK)


class CustomLoginView(LoginView):
    form_class = AuthForm
    http_method_names = ["post", "head", "options"]

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

    def form_invalid(self, form):
        return JsonResponse(data={"errors": form.errors.get('__all__')},
                            status=status.HTTP_401_UNAUTHORIZED)

    def post(self, request, *args, **kwargs):
        super(CustomLoginView, self).post(request, *args, **kwargs)
        data = get_response_data(request=request, user=request.user)
        return JsonResponse(data=data, status=status.HTTP_200_OK)


class CustomLogoutView(LogoutView):                                                     #   /!\ refactor logout using OIDC
    http_method_names = ["post", "head", "options"]

    @method_decorator(csrf_exempt)
    @method_decorator(never_cache)
    def dispatch(self, request, *args, **kwargs):
        if request.method.lower() in self.http_method_names:
            handler = getattr(self, request.method.lower(), self.http_method_not_allowed)
        else:
            handler = self.http_method_not_allowed
        return handler(request, *args, **kwargs)

    @method_decorator(csrf_exempt)
    def post(self, request, *args, **kwargs):
        logout(request)
        return JsonResponse(data={}, status=status.HTTP_200_OK)


@csrf_exempt
def token_refresh_view(request):
    if request.method != "POST":
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)
    return refresh_jwt_token(request.jwt_refresh_key)