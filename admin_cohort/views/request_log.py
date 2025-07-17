import json
from typing import List, Tuple

from drf_spectacular.utils import extend_schema_view, extend_schema
from django_filters import rest_framework as filters, OrderingFilter
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


extended_schema = extend_schema(tags=["Request Logs"])


@extend_schema_view(
    list=extended_schema,
    retrieve=extended_schema,
)
class RequestLogViewSet(viewsets.ModelViewSet):
    queryset = APIRequestLog.objects.all()
    serializer_class = RequestLogSerializer
    http_method_names = ["get"]
    filterset_class = RequestLogFilter
    search_fields = "__all__"
    permission_classes = [LogsPermission]

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            logs: List[APIRequestLog] = list(page)
        else:
            logs: List[APIRequestLog] = list(queryset)

        users = User.objects.filter(pk__in=set([log.username_persistent for log in logs]))
        users_dict = {u.username: u for u in users}

        for log in logs:
            log.related_names = log_related_names(log.response)
            log.user_details = users_dict.get(log.username_persistent)

        serializer = self.serializer_class(logs, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)
