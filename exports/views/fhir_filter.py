from django_filters import rest_framework as filters
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets

from admin_cohort.tools.negative_limit_paginator import NegativeLimitOffsetPagination
from cohort.models import FhirFilter
from cohort.permissions import IsOwnerPermission
from cohort.serializers import FhirFilterSerializer


class FhirFilterFilter(filters.FilterSet):
    ordering = filters.OrderingFilter(fields=('-created_at', 'name'))

    class Meta:
        model = FhirFilter
        fields = ('fhir_resource', 'owner_id', 'created_at')


class FhirFilterViewSet(viewsets.ModelViewSet):
    queryset = FhirFilter.objects.all()
    serializer_class = FhirFilterSerializer
    http_method_names = ["get"]
    permission_classes = [IsOwnerPermission]
    swagger_tags = ['Exports - fhir-filters']
    filterset_class = FhirFilterFilter
    pagination_class = NegativeLimitOffsetPagination
    search_fields = ('$name', '$fhir_resource')

    @swagger_auto_schema(manual_parameters=[openapi.Parameter(name="owner_id", in_=openapi.IN_QUERY, type=openapi.TYPE_STRING)])
    def list(self, request, *args, **kwargs):
        return super(FhirFilterViewSet, self).list(request, *args, **kwargs)
