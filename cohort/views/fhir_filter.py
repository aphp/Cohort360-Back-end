from django_filters import rest_framework as filters
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from admin_cohort.permissions import IsAuthenticated
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
    queryset = FhirFilter.objects.filter(auto_generated=False)
    serializer_class = FhirFilterSerializer
    pagination_class = NegativeLimitOffsetPagination
    filterset_class = FhirFilterFilter
    lookup_field = "uuid"
    http_method_names = ["get", "post", "patch", "delete"]
    permission_classes = [IsAuthenticated]
    swagger_tags = ["Cohort - fhir_filter"]
    logging_methods = ['POST', 'PATCH', 'DELETE']

    @swagger_auto_schema(request_body=openapi.Schema(type=openapi.TYPE_OBJECT,
                                                     properties={"uuids": openapi.Schema(type=openapi.TYPE_ARRAY,
                                                                                         items=openapi.Schema(type=openapi.TYPE_STRING))}),
                         responses={'204': openapi.Response("FhirFilters deleted"),
                                    '500': openapi.Response("One or more IDs is not a valid UUID")})
    @action(methods=['delete'], detail=False)
    def delete_multiple(self, request):
        FhirFilter.objects.filter(uuid__in=request.data.get('uuids', [])).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

