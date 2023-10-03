from django_filters import rest_framework as filters
from rest_framework import viewsets

from admin_cohort.tools.cache import cache_response
from admin_cohort.tools.negative_limit_paginator import NegativeLimitOffsetPagination
from admin_cohort.views import CustomLoggingMixin
from cohort.models import FhirFilter
from cohort.serializers import FhirFilterSerializer


class FhirFilterFilter(filters.FilterSet):
    ordering = filters.OrderingFilter(fields=('-created_at', 'modified_at'))

    class Meta:
        model = FhirFilter
        fields = ('fhir_resource', 'name', 'owner', 'created_at', 'modified_at')


class FhirFilterViewSet(CustomLoggingMixin, viewsets.ModelViewSet):
    queryset = FhirFilter.objects.all()
    serializer_class = FhirFilterSerializer
    pagination_class = NegativeLimitOffsetPagination
    filterset_class = FhirFilterFilter
    lookup_field = "pk"  # Change this line to use "pk" as the lookup field
    swagger_tags = ["Cohort - fhir_filter"]
    http_method_names = ["get", "post", "patch"]
    logging_methods = ['POST', 'PATCH', 'DELETE']

    @cache_response()
    def list(self, request, *args, **kwargs):
        return super(FhirFilterViewSet, self).list(request, *args, **kwargs)
