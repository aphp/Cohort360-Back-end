from django.db.models import Q
from django_filters import rest_framework as filters, OrderingFilter
from rest_framework import viewsets

from admin_cohort.tools import join_qs
from admin_cohort.tools.negative_limit_paginator import NegativeLimitOffsetPagination
from exports.models import Export
from exports.permissions import ExportRequestPermissions
from exports.serializers import ExportSerializer


class ExportFilter(filters.FilterSet):

    def multi_value_filter(self, queryset, field, value: str):
        if value:
            sub_values = [val.strip() for val in value.split(",")]
            return queryset.filter(join_qs([Q(**{field: v}) for v in sub_values]))
        return queryset

    output_format = filters.CharFilter(method="multi_value_filter", field_name="output_format")
    status = filters.CharFilter(method="multi_value_filter", field_name="status")
    name = filters.DateTimeFilter(field_name="name", lookup_expr='icontains')
    motivation = filters.DateTimeFilter(field_name="motivation", lookup_expr='icontains')
    ordering = OrderingFilter(fields=('name',
                                      'insert_datetime',
                                      'output_format',
                                      'status',
                                      ('owner__firstname', 'owner')))

    class Meta:
        model = Export
        fields = ("name",
                  "motivation",
                  "output_format",
                  "status",
                  "owner")


class ExportViewSet(viewsets.ModelViewSet):
    http_method_names = ["get", "post", "patch", "delete"]
    serializer_class = ExportSerializer
    queryset = Export.objects.all()
    swagger_tags = ['Exports - Export']
    filterset_class = ExportFilter
    pagination_class = NegativeLimitOffsetPagination
    permission_classes = (ExportRequestPermissions,)
    search_fields = ("name",
                     "owner__provider_username",
                     "owner__firstname",
                     "owner__lastname",
                     "request_job_status",
                     "output_format",
                     "target_name",
                     "target_unix_account__name")

