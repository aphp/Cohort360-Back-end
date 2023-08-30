from django_filters import rest_framework as filters, OrderingFilter
from rest_framework import viewsets

from admin_cohort.tools.negative_limit_paginator import NegativeLimitOffsetPagination
from exports.models import ExportResultStat
from exports.permissions import ExportRequestPermissions
from exports.serializers import ExportResultStatSerializer


class ExportResultStatFilter(filters.FilterSet):
    name = filters.DateTimeFilter(field_name="name", lookup_expr='icontains')
    export_name = filters.CharFilter(field_name="export__name", lookup_expr="icontains")
    ordering = OrderingFilter(fields=("name",
                                      "type",
                                      "value",
                                      ("export__name", "export")))

    class Meta:
        model = ExportResultStat
        fields = ("name",
                  "export",
                  "export_name",
                  "type")


class ExportResultStatViewSet(viewsets.ModelViewSet):
    http_method_names = ["get", "post", "patch", "delete"]
    serializer_class = ExportResultStatSerializer
    queryset = ExportResultStat.objects.all()
    swagger_tags = ['Exports - ExportResultStat']
    filterset_class = ExportResultStatFilter
    pagination_class = NegativeLimitOffsetPagination
    permission_classes = (ExportRequestPermissions,)

