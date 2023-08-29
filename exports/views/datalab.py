from django_filters import rest_framework as filters, OrderingFilter
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets

from admin_cohort.permissions import either
from admin_cohort.tools.negative_limit_paginator import NegativeLimitOffsetPagination
from admin_cohort.types import JobStatus
from cohort.models import CohortResult
from cohort.permissions import IsOwner
from exports.models import Datalab
from exports.permissions import AnnexesPermissions, can_review_transfer_jupyter, can_review_export_csv


class DatalabFilter(filters.FilterSet):
    ordering = OrderingFilter(fields=('name', 'created_at'))

    class Meta:
        model = CohortResult
        fields = ('owner_id',)


class DatalabViewSet(viewsets.ModelViewSet):
    lookup_field = "id"
    http_method_names = ["get", "post", "patch", "delete"]
    serializer_class = DatalabSerializer
    queryset = Datalab.objects.all()
    swagger_tags = ['Exports - Datalab']
    filterset_class = DatalabFilter
    pagination_class = NegativeLimitOffsetPagination
    search_fields = ('$name', '$description')
    permission_classes = (AccountPermissions,)

