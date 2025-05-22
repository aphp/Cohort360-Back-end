from django.db.utils import IntegrityError
from django_filters import rest_framework as filters
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from admin_cohort.permissions import IsAuthenticated
from admin_cohort.tools.cache import cache_response
from cohort.models import FhirFilter
from cohort.serializers import FhirFilterSerializer, FhirFilterCreateSerializer, FhirFilterPatchSerializer
from cohort.views.shared import UserObjectsRestrictedViewSet


class FhirFilterFilter(filters.FilterSet):
    fhir_filter = filters.CharFilter(field_name='filter', lookup_expr='icontains')
    fhir_resource = filters.CharFilter(field_name='fhir_resource', lookup_expr='icontains')
    name = filters.CharFilter(field_name='name', lookup_expr='icontains')
    ordering = filters.OrderingFilter(fields=('-created_at', 'modified_at'))

    class Meta:
        model = FhirFilter
        fields = ('name',
                  'owner',
                  'fhir_resource',
                  'fhir_filter',
                  'query_version')


class FhirFilterViewSet(UserObjectsRestrictedViewSet):
    queryset = FhirFilter.objects.filter(auto_generated=False)
    serializer_class = FhirFilterSerializer
    filterset_class = FhirFilterFilter
    http_method_names = ["get", "post", "patch", "delete"]
    permission_classes = [IsAuthenticated]
    swagger_tags = ["FHIR Filters"]

    @extend_schema(responses={status.HTTP_200_OK: FhirFilterSerializer})
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(responses={status.HTTP_200_OK: FhirFilterSerializer(many=True)})
    @cache_response()
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(request=FhirFilterCreateSerializer,
                   responses={status.HTTP_201_CREATED: FhirFilterSerializer})
    def create(self, request, *args, **kwargs):
        try:
            return super().create(request, *args, **kwargs)
        except IntegrityError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(request=FhirFilterPatchSerializer,
                   responses={status.HTTP_200_OK: FhirFilterSerializer})
    def partial_update(self, request, *args, **kwargs):
        try:
            return super().partial_update(request, *args, **kwargs)
        except IntegrityError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(responses={status.HTTP_204_NO_CONTENT: None})
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    @extend_schema(responses={status.HTTP_204_NO_CONTENT: None})
    @action(methods=['delete'], detail=False)
    def delete_multiple(self, request):
        FhirFilter.objects.filter(uuid__in=request.data.get('uuids', [])).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

