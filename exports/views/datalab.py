from django_filters import rest_framework as filters, OrderingFilter
from rest_framework import viewsets

from admin_cohort.tools.negative_limit_paginator import NegativeLimitOffsetPagination
from exports.models import Datalab
from exports.permissions import ExportRequestPermissions
from exports.serializers import DatalabSerializer


class DatalabFilter(filters.FilterSet):
    ordering = OrderingFilter(fields=('created_datetime',))

    class Meta:
        model = Datalab
        fields = ('infrastructure_provider',)


class DatalabViewSet(viewsets.ModelViewSet):
    http_method_names = ["get", "post", "patch", "delete"]
    serializer_class = DatalabSerializer
    queryset = Datalab.objects.all()
    swagger_tags = ['Exports - Datalab']
    filterset_class = DatalabFilter
    search_fields = ("infrastructure_provider__name",)
    pagination_class = NegativeLimitOffsetPagination
    permission_classes = (ExportRequestPermissions,)

