from django_filters import rest_framework as filters, OrderingFilter
from rest_framework import viewsets

from admin_cohort.tools.negative_limit_paginator import NegativeLimitOffsetPagination
from exports.models import ExportTable
from exports.permissions import ExportRequestPermissions
from exports.serializers import ExportTableSerializer


class ExportTableFilter(filters.FilterSet):

    name = filters.DateTimeFilter(field_name="name", lookup_expr='icontains')
    export_name = filters.CharFilter(field_name="export__name", lookup_expr="icontains")
    cohort_result_subset_name = filters.CharFilter(field_name="cohort_result_subset__name", lookup_expr="icontains")
    filter_name = filters.CharFilter(field_name="filter__name", lookup_expr="icontains")
    ordering = OrderingFilter(fields=('name',))

    class Meta:
        model = ExportTable
        fields = ("name",
                  "export",
                  "export_name",
                  "cohort_result_subset",
                  "cohort_result_subset_name",
                  "filter",
                  "filter_name")


class ExportTableViewSet(viewsets.ModelViewSet):
    http_method_names = ["get", "post", "patch", "delete"]
    serializer_class = ExportTableSerializer
    queryset = ExportTable.objects.all()
    swagger_tags = ['Exports - ExportTable']
    filterset_class = ExportTableFilter
    pagination_class = NegativeLimitOffsetPagination
    permission_classes = (ExportRequestPermissions,)

