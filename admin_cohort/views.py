import json
from typing import List, Tuple

import django_filters
from django.contrib.auth import login
from django.contrib.auth.views import LoginView
from django.http import HttpRequest, HttpResponse
from django.http import HttpResponseRedirect, Http404, JsonResponse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.debug import sensitive_post_parameters
from drf_yasg import openapi
from rest_framework.decorators import action

from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework_tracking.mixins import LoggingMixin
from rest_framework_tracking.models import APIRequestLog

from accesses.models import Access, Profile
from accesses.serializers import AccessSerializer, ProfileSerializer
from admin_cohort import conf_auth
from .MaintenanceModeMiddleware import get_next_maintenance
from .models import User, get_user, MaintenancePhase
from .permissions import LogsPermission, IsAuthenticatedReadOnly, \
    OR, can_user_read_users, MaintenancePermission
from .serializers import APIRequestLogSerializer, \
    UserSerializer, OpenUserSerializer, MaintenancePhaseSerializer
from .settings import MANUAL_SOURCE


class YarnReadOnlyViewsetMixin:
    @swagger_auto_schema(auto_schema=None)
    def create(self, request, *args, **kwargs):
        super(YarnReadOnlyViewsetMixin, self).create(self, request, *args,
                                                     **kwargs)

    @swagger_auto_schema(auto_schema=None)
    def destroy(self, request, *args, **kwargs):
        super(YarnReadOnlyViewsetMixin, self).destroy(self, request, *args,
                                                      **kwargs)

    @swagger_auto_schema(auto_schema=None)
    def partial_update(self, request, *args, **kwargs):
        super(YarnReadOnlyViewsetMixin, self).partial_update(self, request,
                                                             *args, **kwargs)

    @swagger_auto_schema(auto_schema=None)
    def update(self, request, *args, **kwargs):
        super(YarnReadOnlyViewsetMixin, self).update(self, request, *args,
                                                     **kwargs)


class BaseViewset(viewsets.ModelViewSet):
    def get_serializer_context(self):
        return {'request': self.request}

    def perform_destroy(self, instance):
        instance.delete_datetime = timezone.now()
        instance.save()


class CustomLoggingMixin(LoggingMixin):
    def handle_log(self):
        for f in ['data', 'errors', 'response']:
            v = self.log.get(f, None)
            if isinstance(v, dict) or isinstance(v, list):
                try:
                    self.log[f] = json.dumps(v)
                except Exception:
                    pass

        return super(CustomLoggingMixin, self).handle_log()


class LogFilter(django_filters.FilterSet):
    def method_filter(self, queryset, field, value):
        return queryset.filter(
            **{f'{field}__in': str(value).upper().split(",")}
        )

    def status_code_filter(self, queryset, field, value):
        return queryset.filter(
            **{f'{field}__in': [int(v) for v in str(value).upper().split(",")]}
        )

    method = django_filters.CharFilter(method='method_filter')
    status_code = django_filters.CharFilter(method='status_code_filter')
    requested_at = django_filters.DateTimeFromToRangeFilter()
    response_ms = django_filters.RangeFilter()
    # path = django_filters.CharFilter(lookup_expr='icontains')
    path_contains = django_filters.CharFilter(
        field_name='path', lookup_expr='icontains'
    )
    response = django_filters.CharFilter(
        field_name='response', lookup_expr='icontains'
    )
    errors = django_filters.CharFilter(
        field_name='errors', lookup_expr='icontains'
    )
    data = django_filters.CharFilter(
        field_name='data', lookup_expr='icontains'
    )

    class Meta:
        model = APIRequestLog
        fields = [f.name for f in APIRequestLog._meta.fields] + [
            'path_contains'
        ]


def log_related_names(log_data: dict):
    try:
        d = json.loads(log_data)
    except Exception:
        return None

    if not isinstance(d, dict):
        return None

    def retrieve_object_names(o: dict) -> List[Tuple[str, str]]:
        return [
                   (k, v) for (k, v) in o.items()
                   if k.endswith('name') and isinstance(v, str)
               ] + sum([retrieve_object_names(v)
                        for v in o.values() if isinstance(v, dict)], [])

    return dict(retrieve_object_names(d))


class LoggingViewset(YarnReadOnlyViewsetMixin, viewsets.ModelViewSet):
    queryset = APIRequestLog.objects.all()
    serializer_class = APIRequestLogSerializer
    filterset_fields = "__all__"
    FILTERS_DEFAULT_LOOKUP_EXPR = "contains"
    filter_class = LogFilter
    ordering_fields = "__all__"
    search_fields = "__all__"

    permission_classes = [LogsPermission, ]

    @swagger_auto_schema(manual_parameters=list(map(
        lambda x: openapi.Parameter(
            name=x[0], in_=openapi.IN_QUERY, description=x[1], type=x[2],
            format=x[3] if len(x) == 4 else None
        ), [
            ["id", "L'ID d'une ligne de log", openapi.TYPE_INTEGER],
            ["user", "Code APH de l'utilisateur", openapi.TYPE_INTEGER],
            [
                "requested_at_after", "Date de début de période d'étude",
                openapi.TYPE_STRING, openapi.FORMAT_DATETIME
            ],
            [
                "requested_at_before", "Date de fin de période d'étude",
                openapi.TYPE_STRING, openapi.FORMAT_DATETIME
            ],
            [
                "response_ms_min", "Temps de réponse minimale",
                openapi.TYPE_NUMBER
            ],
            [
                "response_ms_max", "Temps de réponse maximale",
                openapi.TYPE_NUMBER
            ],
            ["path", "Url exact utilisée", openapi.TYPE_STRING],
            [
                "path_contains", "Est contenu dans l'url utilisée",
                openapi.TYPE_STRING
            ],
            ["view", "View de django exacte", openapi.TYPE_STRING],
            [
                "view_method", "Méthode de view de django exacte",
                openapi.TYPE_STRING
            ],
            [
                "remote_addr", "Adresse IP de l'utilisateur",
                openapi.TYPE_STRING
            ],
            [
                "host", "Adresse d'origine de la requête",
                openapi.TYPE_STRING
            ],
            [
                "method", "Méthode HTTP utilisée, peut-être multiple, séparée"
                          " par ','", openapi.TYPE_STRING
            ],
            [
                "query_params", "Contenu dans les paramètres de requête "
                                "(préférer 'data')", openapi.TYPE_STRING
            ],
            [
                "data", "Contenu dans les données de la requête",
                openapi.TYPE_STRING
            ],
            [
                "response", "Contenu dans les données retournées par le "
                            "back-end", openapi.TYPE_STRING
            ],
            [
                "errors", "Contenu dans les données retournées par le back-end "
                          "dans le cas d'une erreur", openapi.TYPE_STRING
            ],

            [
                "status_code", "Code HTTP renvoyé, peut-être multiple "
                               "séparé par ','", openapi.TYPE_STRING
            ],
            [
                "ordering",
                f"Champs possible (field ou -field): "
                f"{', '.join([f.name for f in APIRequestLog._meta.fields])}",
                openapi.TYPE_STRING
            ],
            [
                "search", "Cherchera dans tous les champs cités pour ordering",
                openapi.TYPE_STRING
            ],
            [
                "page", "Page voulue", openapi.TYPE_NUMBER
            ],
        ])),
        operation_description="""
        Exemple de requêtes:
        **Actions réalisées par un utilisateur spécifique:**
        -> user={codeAph}

        **Actions d'une date à une autre:**
        -> requested_at_after=dateDebut ; requested_at_before=dateFin

        **Actions liées indirectement à un périmètre
        (sur un accès par exemple):**
        -> response="perimeter_id": {id},

        **Actions faites sur un accès spécifique:**
        -> path=/accesses/{access_id}/

        **Action qui a créé un accès:**
        -> path=/accesses/ ; result="perimeter_id": {id},
        """
    )
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            completed_data: List[APIRequestLog] = list(page)
        else:
            completed_data: List[APIRequestLog] = list(queryset)

        from admin_cohort.models import User
        full_users = User.objects.filter(
            provider_username__in=list(set(
                [ll.username_persistent for ll in completed_data]
            ))
        )
        dct_users = dict([(p.provider_username, p) for p in full_users])

        for o in completed_data:
            o.related_names = log_related_names(o.response)
            o.user_details = dct_users.get(o.username_persistent, None)

        serializer = self.get_serializer(completed_data, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)


class CustomLoginView(LoginView):
    @csrf_exempt
    def form_valid(self, form):
        """Security check complete. Log the user in."""
        login(self.request, form.get_user())

        user = UserSerializer(
            get_user(self.request.user.provider_username)
        ).data

        valid_profiles = ProfileSerializer(
            [ph for ph in
             Profile.objects.filter(user_id=user["provider_username"])
             if ph.is_valid and ph.source == MANUAL_SOURCE],
            many=True
        )

        # TODO for RESt API: being returned with users/:user_id/accesses
        accesses = AccessSerializer(
            [
                a for a in
                Access.objects.filter(
                    profile_id__in=[
                        p["id"] for p in valid_profiles.data
                    ]).all()
                if a.is_valid],
            many=True
        ).data
        data = dict(
            provider=user,
            user=user,
            session_id=self.request.session.session_key,
            accesses=accesses,
            jwt=dict(
                access=self.request.jwt_session_key,
                refresh=self.request.jwt_refresh_key,
                last_connection=getattr(self.request, 'last_connection', dict())
            )
        )
        # when ready, try removing jwt field (so that does not process it,
        # because it should be done with cookies only)
        # data = dict(provider=provider,
        # session_id=self.request.session.session_key, accesses=accesses)
        url = self.get_redirect_url()
        return JsonResponse(data) if not url else HttpResponseRedirect(url)

    @method_decorator(sensitive_post_parameters())
    @csrf_exempt
    @method_decorator(never_cache)
    def dispatch(self, request, *args, **kwargs):
        if self.redirect_authenticated_user \
                and self.request.user.is_authenticated:
            redirect_to = self.get_success_url()
            if redirect_to == self.request.path:
                raise ValueError(
                    "Redirection loop for authenticated user detected."
                    " Check that your LOGIN_REDIRECT_URL doesn't "
                    "point to a login page."
                )
            return HttpResponseRedirect(redirect_to)
        if request.method.lower() in self.http_method_names:
            handler = getattr(self, request.method.lower(),
                              self.http_method_not_allowed)
        else:
            handler = self.http_method_not_allowed
        return handler(request, *args, **kwargs)

    @csrf_exempt
    def post(self, request, *args, **kwargs):
        resp = super(CustomLoginView, self).post(request, *args, **kwargs)
        if getattr(request, 'jwt_server_unavailable', False):
            return HttpResponse(
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
                content=getattr(request, 'jwt_server_message', ""))
        return resp


@csrf_exempt
def redirect_token_refresh_view(request):
    if request.method != "POST":
        raise Http404()

    try:
        res = conf_auth.refresh_jwt(request.jwt_refresh_key)
    except Exception as e:
        raise Http404(e)

    return JsonResponse(data=res.__dict__)


# to deprecate
def maintenance_view(request: HttpRequest):
    q = (
            MaintenancePhase.objects.filter(start_datetime__gte=timezone.now())
            |
            MaintenancePhase.objects.filter(
                start_datetime__lte=timezone.now(),
                end_datetime__gte=timezone.now())
    ).order_by('start_datetime').first()
    return JsonResponse(MaintenancePhaseSerializer(q).data,
                        status=status.HTTP_200_OK)


class MaintenancePhaseViewSet(viewsets.ModelViewSet):
    queryset = MaintenancePhase.objects.all()
    ordering_fields = ("start_datetime", "end_datetime")
    lookup_field = "id"
    search_fields = ["subject"]
    filterset_fields = ["subject", "start_datetime", "end_datetime"]
    http_method_names = ["get", "delete", "post", "patch"]
    permission_classes = (MaintenancePermission,)
    serializer_class = MaintenancePhaseSerializer

    @swagger_auto_schema(
        operation_description=(
                "Returns next maintenance if exists. Next maintenance is "
                "either: "
                "\n- the one currently active. If several, the one with "
                "the biggest end_datetime"
                "\n- if existing, and if no currently active, "
                "the one with smallest start_datetime that is bigger than now"),
        responses={200: openapi.Response(
            'There is a coming or current maintenance. '
            'The response can be null otherwise.', MaintenancePhaseSerializer)
        }
    )
    @action(methods=['get'], detail=False, url_path='next')
    def next(self, request, *args, **kwargs):
        q = get_next_maintenance()
        d = self.get_serializer(q).data if q is not None else {}
        return Response(d)


class UserViewSet(YarnReadOnlyViewsetMixin, BaseViewset):
    queryset = User.objects.all()
    lookup_field = "provider_username"
    filterset_fields = ['firstname', "lastname", "provider_username", "email"]
    ordering_fields = (
        "firstname",
        "lastname",
        "provider_username",
        "email",
    )
    search_fields = ["firstname", "lastname", "provider_username", "email"]

    def get_serializer_context(self):
        return {'request': self.request}

    def get_permissions(self):
        return OR(IsAuthenticatedReadOnly(), )

    def get_serializer(self, *args, **kwargs):
        return UserSerializer(*args, **kwargs) \
            if can_user_read_users(self.request.user) \
            else OpenUserSerializer(*args, **kwargs)

    def get_queryset(self):
        # todo : to test manualonly
        manual_only = self.request.GET.get("manual_only", None)
        if not manual_only:
            return super(UserViewSet, self).get_queryset()

        return User.objects.filter(profiles__source='Manual').distinct()

    @swagger_auto_schema(
        manual_parameters=list(map(
            lambda x: openapi.Parameter(
                name=x[0], in_=openapi.IN_QUERY, description=x[1], type=x[2],
                pattern=x[3] if len(x) == 4 else None
            ), [
                [
                    "manual_only",
                    "If True, only returns providers with a manual "
                    "provider_history",
                    openapi.TYPE_BOOLEAN
                ],
                ["firstname", "Search type", openapi.TYPE_STRING],
                ["lastname", "Filter type", openapi.TYPE_STRING],
                ["provider_username", "Search type", openapi.TYPE_STRING],
                ["provider_source_value", "Search type", openapi.TYPE_STRING],
                ["email", "Search type", openapi.TYPE_STRING],
                [
                    "ordering",
                    "Which field to use when ordering the results "
                    "(firstname, lastname, "
                    "provider_username (provider_source_value), email)",
                    openapi.TYPE_STRING
                ],
                [
                    "search",
                    "A search term on multiple fields ("
                    "firstname, lastname, "
                    "provider_username (provider_source_value), email)",
                    openapi.TYPE_STRING
                ],
                [
                    "page", "A page number within the paginated result set.",
                    openapi.TYPE_INTEGER
                ],
            ])))
    def list(self, request, *args, **kwargs):
        # todo: double check
        if 'provider_source_value' in self.request.GET:
            request.GET._mutable = True
            self.request.GET['provider_username'] = \
                self.request.GET.get('provider_source_value')
        if 'provider_source_value' in self.request.GET.get('ordering', ''):
            self.request.GET['ordering'] = \
                self.request.GET.get('ordering') \
                    .replace('provider_source_value', 'provider_username')
        return super(UserViewSet, self).list(request, *args, **kwargs)
