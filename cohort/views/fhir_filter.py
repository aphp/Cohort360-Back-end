from django_filters import rest_framework as filters

from admin_cohort.permissions import IsAuthenticated
from admin_cohort.tools.cache import cache_response
from admin_cohort.tools.negative_limit_paginator import NegativeLimitOffsetPagination
from cohort.models import FhirFilter
from cohort.serializers import FhirFilterSerializer
from cohort.views.shared import UserObjectsRestrictedViewSet


class FhirFilterFilter(filters.FilterSet):
    ordering = filters.OrderingFilter(fields=('-created_at', 'modified_at'))

    class Meta:
        model = FhirFilter
        fields = ('fhir_resource', 'name', 'owner', 'created_at', 'modified_at')


class FhirFilterViewSet(UserObjectsRestrictedViewSet):
    queryset = FhirFilter.objects.all()
    serializer_class = FhirFilterSerializer
    pagination_class = NegativeLimitOffsetPagination
    filterset_class = FhirFilterFilter
    lookup_field = "uuid"
    http_method_names = ["get", "post", "patch"]
    permission_classes = [IsAuthenticated]
    swagger_tags = ["Cohort - fhir_filter"]

    @cache_response()
    def list(self, request, *args, **kwargs):
        return super(FhirFilterViewSet, self).list(request, *args, **kwargs)
