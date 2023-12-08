import json
from typing import List, Tuple

from django_filters import rest_framework as filters, OrderingFilter
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework_tracking.models import APIRequestLog

from admin_cohort.models import User
from admin_cohort.permissions import LogsPermission
from admin_cohort.serializers import RequestLogSerializer


class RequestLogFilter(filters.FilterSet):
    def method_filter(self, queryset, field, value):
        return queryset.filter(**{f'{field}__in': str(value).upper().split(",")})

    def status_code_filter(self, queryset, field, value):
        return queryset.filter(**{f'{field}__in': [int(v) for v in str(value).upper().split(",")]})

    method = filters.CharFilter(method='method_filter')
    status_code = filters.CharFilter(method='status_code_filter')
    requested_at = filters.DateTimeFromToRangeFilter()
    response_ms = filters.RangeFilter()
    path_contains = filters.CharFilter(field_name='path', lookup_expr='icontains')
    response = filters.CharFilter(field_name='response', lookup_expr='icontains')
    errors = filters.CharFilter(field_name='errors', lookup_expr='icontains')
    data = filters.CharFilter(field_name='data', lookup_expr='icontains')

    ordering = OrderingFilter(fields=('requested_at',))

    class Meta:
        model = APIRequestLog
        fields = [f.name for f in APIRequestLog._meta.fields] + ['path_contains']


def log_related_names(log_data: str):
    try:
        d = json.loads(log_data)
    except Exception:
        return None

    if not isinstance(d, dict):
        return None

    def retrieve_object_names(record: dict) -> List[Tuple[str, str]]:
        return [(k, v) for (k, v) in record.items() if k.endswith('name') and isinstance(v, str)] \
                + sum([retrieve_object_names(v)
                       for v in record.values() if isinstance(v, dict)], [])

    return dict(retrieve_object_names(d))


class RequestLogViewSet(viewsets.ModelViewSet):
    queryset = APIRequestLog.objects.all()
    serializer_class = RequestLogSerializer
    http_method_names = ["get"]
    filterset_class = RequestLogFilter
    search_fields = "__all__"
    permission_classes = [LogsPermission]

    @swagger_auto_schema(manual_parameters=list(map(
        lambda x: openapi.Parameter(name=x[0], in_=openapi.IN_QUERY, description=x[1], type=x[2], format=x[3] if len(x) == 4 else None),
        [["id", "L'ID d'une ligne de log", openapi.TYPE_INTEGER],
         ["user", "Code APH de l'utilisateur", openapi.TYPE_INTEGER],
         ["requested_at_after", "Date de début de période d'étude", openapi.TYPE_STRING, openapi.FORMAT_DATETIME],
         ["requested_at_before", "Date de fin de période d'étude", openapi.TYPE_STRING, openapi.FORMAT_DATETIME],
         ["response_ms_min", "Temps de réponse minimale", openapi.TYPE_NUMBER],
         ["response_ms_max", "Temps de réponse maximale", openapi.TYPE_NUMBER],
         ["path", "Url exact utilisée", openapi.TYPE_STRING],
         ["path_contains", "Est contenu dans l'url utilisée", openapi.TYPE_STRING],
         ["view", "View de django exacte", openapi.TYPE_STRING],
         ["view_method", "Méthode de view de django exacte", openapi.TYPE_STRING],
         ["remote_addr", "Adresse IP de l'utilisateur", openapi.TYPE_STRING],
         ["host", "Adresse d'origine de la requête", openapi.TYPE_STRING],
         ["method", "Méthode HTTP utilisée, peut-être multiple, séparée par ','", openapi.TYPE_STRING],
         ["query_params", "Contenu dans les paramètres de requête (préférer 'data')", openapi.TYPE_STRING],
         ["data", "Contenu dans les données de la requête", openapi.TYPE_STRING],
         ["response", "Contenu dans les données retournées par le back-end", openapi.TYPE_STRING],
         ["errors", "Contenu dans les données retournées par le back-end dans le cas d'une erreur", openapi.TYPE_STRING],
         ["status_code", "Code HTTP renvoyé, peut-être multiple séparé par ','", openapi.TYPE_STRING],
         ["ordering", f"Champs possible (field ou -field): {', '.join([f.name for f in APIRequestLog._meta.fields])}", openapi.TYPE_STRING],
         ["search", "Cherchera dans tous les champs cités pour ordering", openapi.TYPE_STRING],
         ["page", "Page voulue", openapi.TYPE_NUMBER]])))
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            logs: List[APIRequestLog] = list(page)
        else:
            logs: List[APIRequestLog] = list(queryset)

        users = User.objects.filter(pk__in=set([log.username_persistent for log in logs]))
        dct_users = dict((u.pk, u) for u in users)

        for log in logs:
            log.related_names = log_related_names(log.response)
            log.user_details = dct_users.get(log.username_persistent)

        serializer = self.serializer_class(logs, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)
