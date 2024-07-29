from django.http import QueryDict
from django_filters import rest_framework as filters, OrderingFilter
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework_extensions.mixins import NestedViewSetMixin

from admin_cohort.tools.cache import cache_response
from admin_cohort.tools.negative_limit_paginator import NegativeLimitOffsetPagination
from cohort.models import Request
from cohort.serializers import RequestSerializer, RequestPatchSerializer, RequestCreateSerializer
from cohort.views.shared import UserObjectsRestrictedViewSet


class RequestFilter(filters.FilterSet):
    ordering = OrderingFilter(fields=('name', 'created_at', 'modified_at', 'favorite', 'data_type_of_query'))

    class Meta:
        model = Request
        fields = ('uuid', 'name', 'favorite', 'data_type_of_query', 'parent_folder', 'shared_by')


class RequestViewSet(NestedViewSetMixin, UserObjectsRestrictedViewSet):
    queryset = Request.objects.all()
    serializer_class = RequestSerializer
    http_method_names = ["get", "post", "patch", "delete"]
    lookup_field = "uuid"
    swagger_tags = ["Requests"]
    pagination_class = NegativeLimitOffsetPagination
    filterset_class = RequestFilter
    search_fields = ("$name", "$description",)

    @extend_schema(tags=swagger_tags,
                   responses={status.HTTP_200_OK: RequestSerializer})
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(tags=swagger_tags,
                   responses={status.HTTP_200_OK: RequestSerializer})
    @cache_response()
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(tags=swagger_tags,
                   request=RequestCreateSerializer,
                   responses={status.HTTP_201_CREATED: RequestSerializer})
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(tags=swagger_tags,
                   request=RequestPatchSerializer,
                   responses={status.HTTP_200_OK: RequestSerializer})
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(tags=swagger_tags,
                   responses={status.HTTP_204_NO_CONTENT: None})
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)


class NestedRequestViewSet(RequestViewSet):

    @extend_schema(tags=RequestViewSet.swagger_tags,
                   request=RequestCreateSerializer,
                   responses={status.HTTP_201_CREATED: RequestSerializer})
    def create(self, request, *args, **kwargs):
        if type(request.data) is QueryDict:
            request.data._mutable = True
        if 'parent_folder' in kwargs:
            request.data["parent_folder"] = kwargs['parent_folder']
        return super().create(request, *args, **kwargs)
