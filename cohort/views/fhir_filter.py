from django_filters import rest_framework as filters
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from admin_cohort.permissions import IsAuthenticated
from admin_cohort.tools.cache import cache_response
from admin_cohort.tools.negative_limit_paginator import NegativeLimitOffsetPagination
from cohort.models import FhirFilter
from cohort.serializers import FhirFilterSerializer, FhirFilterCreateSerializer, FhirFilterPatchSerializer
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
    http_method_names = ["get", "post", "patch", "delete"]
    permission_classes = [IsAuthenticated]
    swagger_tags = ["FHIR Filters"]
    logging_methods = ['POST', 'PATCH', 'DELETE']

    @extend_schema(tags=swagger_tags,
                   responses={status.HTTP_200_OK: FhirFilterSerializer})
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(tags=swagger_tags,
                   responses={status.HTTP_200_OK: FhirFilterSerializer})
    @cache_response()
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(tags=swagger_tags,
                   request=FhirFilterCreateSerializer,
                   responses={status.HTTP_201_CREATED: FhirFilterSerializer})
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(tags=swagger_tags,
                   request=FhirFilterPatchSerializer,
                   responses={status.HTTP_200_OK: FhirFilterSerializer})
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(tags=swagger_tags,
                   responses={status.HTTP_204_NO_CONTENT: None})
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    @extend_schema(tags=swagger_tags,
                   responses={status.HTTP_204_NO_CONTENT: None})
    @action(methods=['delete'], detail=False)
    def delete_multiple(self, request):
        FhirFilter.objects.filter(uuid__in=request.data.get('uuids', [])).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

