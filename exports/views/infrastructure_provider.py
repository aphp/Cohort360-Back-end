from django_filters import rest_framework as filters, OrderingFilter
from rest_framework import viewsets

from admin_cohort.tools.negative_limit_paginator import NegativeLimitOffsetPagination
from exports.models import InfrastructureProvider
from exports.permissions import ExportRequestPermissions
from exports.serializers import InfrastructureProviderSerializer


class InfrastructureProviderFilter(filters.FilterSet):
    ordering = OrderingFilter(fields=('name',))

    class Meta:
        model = InfrastructureProvider
        fields = "__all__"


class InfrastructureProviderViewSet(viewsets.ModelViewSet):
    http_method_names = ["get", "post", "patch", "delete"]
    serializer_class = InfrastructureProviderSerializer
    queryset = InfrastructureProvider.objects.all()
    swagger_tags = ['Exports - InfrastructureProvider']
    filterset_class = InfrastructureProviderFilter
    search_fields = ("infrastructure_provider__name",)
    pagination_class = NegativeLimitOffsetPagination
    permission_classes = (ExportRequestPermissions,)

