from django_filters import rest_framework as filters

from cohort.models import FhirFilter
from cohort.permissions import IsOwnerPermission
from cohort.serializers import FhirFilterSerializer
from exports.views import ExportsBaseViewSet


class FhirFilterFilter(filters.FilterSet):
    ordering = filters.OrderingFilter(fields=('-created_at', 'name'))

    class Meta:
        model = FhirFilter
        fields = ('fhir_resource', 'owner_id', 'created_at')


class FhirFilterViewSet(ExportsBaseViewSet):
    queryset = FhirFilter.objects.all()
    serializer_class = FhirFilterSerializer
    http_method_names = ["get"]
    permission_classes = [IsOwnerPermission]
    swagger_tags = ['Exports - FHIR Filters']
    filterset_class = FhirFilterFilter
    search_fields = ('$name', '$fhir_resource')

