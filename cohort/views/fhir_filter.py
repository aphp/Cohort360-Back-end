from django_filters import rest_framework as filters
from rest_framework import viewsets
from rest_framework.pagination import LimitOffsetPagination

from admin_cohort.tools.cache import cache_response
from cohort.models import FhirFilter
from cohort.serializers import FhirFilterSerializer


class FhirFilterFilter(filters.FilterSet):
    ordering = filters.OrderingFilter(fields=('-created_at', 'modified_at'))

    class Meta:
        model = FhirFilter
        fields = ('fhir_resource', 'name', 'owner', 'created_at', 'modified_at')


class FhirFilterViewSet(viewsets.ModelViewSet):
    queryset = FhirFilter.objects.all()
    serializer_class = FhirFilterSerializer
    pagination_class = LimitOffsetPagination
    filterset_class = FhirFilterFilter
    lookup_field = "pk"  # Change this line to use "pk" as the lookup field
    swagger_tags = ["Cohort - fhir_filter"]
    http_method_names = ["get", "post", "patch"]

    @cache_response()
    def list(self, request, *args, **kwargs):
        return super(FhirFilterViewSet, self).list(request, *args, **kwargs)
