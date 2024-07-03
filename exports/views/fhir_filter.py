import json

from django_filters import rest_framework as filters
from drf_spectacular.utils import extend_schema_view, extend_schema
from rest_framework import status
from rest_framework.response import Response

from cohort.models import FhirFilter
from cohort.permissions import IsOwnerPermission
from cohort.serializers import FhirFilterSerializer
from exports.views import ExportsBaseViewSet


class FhirFilterFilter(filters.FilterSet):
    ordering = filters.OrderingFilter(fields=('-created_at', 'name'))

    class Meta:
        model = FhirFilter
        fields = ('fhir_resource', 'owner_id')


@extend_schema_view(retrieve=extend_schema(exclude=True))
class FhirFilterViewSet(ExportsBaseViewSet):
    queryset = FhirFilter.objects.filter(auto_generated=False)
    serializer_class = FhirFilterSerializer
    http_method_names = ["get"]
    permission_classes = [IsOwnerPermission]
    swagger_tags = ['Exports - FHIR Filters']
    filterset_class = FhirFilterFilter
    search_fields = ('$name', '$fhir_resource', '$filter')

    def list(self, request, *args, **kwargs):
        fhir_filters = self.filter_queryset(self.get_queryset())
        if json.loads(request.query_params.get("pseudo_mode", "false")):
            fhir_filters = fhir_filters.filter(identifying=False)
        return Response(data=self.serializer_class(fhir_filters, many=True).data,
                        status=status.HTTP_200_OK)
