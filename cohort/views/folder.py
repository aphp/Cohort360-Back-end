from django_filters import rest_framework as filters, OrderingFilter
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework_extensions.mixins import NestedViewSetMixin

from admin_cohort.tools.cache import cache_response
from admin_cohort.tools.negative_limit_paginator import NegativeLimitOffsetPagination
from cohort.models import Folder
from cohort.serializers import FolderSerializer, FolderCreateSerializer, FolderPatchSerializer
from cohort.views.shared import UserObjectsRestrictedViewSet


class FolderFilter(filters.FilterSet):
    ordering = OrderingFilter(fields=('name', 'created_at', 'modified_at'))

    class Meta:
        model = Folder
        fields = ['uuid', 'name']


class FolderViewSet(NestedViewSetMixin, UserObjectsRestrictedViewSet):
    queryset = Folder.objects.all()
    serializer_class = FolderSerializer
    http_method_names = ['get', 'post', 'patch', 'delete']
    lookup_field = "uuid"
    swagger_tags = ['Folders']
    logging_methods = ['POST', 'PATCH', 'DELETE']
    pagination_class = NegativeLimitOffsetPagination
    filterset_class = FolderFilter
    search_fields = ('$name',)

    @extend_schema(tags=swagger_tags,
                   responses={status.HTTP_200_OK: FolderSerializer})
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(tags=swagger_tags,
                   responses={status.HTTP_200_OK: FolderSerializer})
    @cache_response()
    def list(self, request, *args, **kwargs):
        return super(FolderViewSet, self).list(request, *args, **kwargs)

    @extend_schema(tags=swagger_tags,
                   request=FolderCreateSerializer,
                   responses={status.HTTP_201_CREATED: FolderSerializer})
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(tags=swagger_tags,
                   request=FolderPatchSerializer,
                   responses={status.HTTP_200_OK: FolderSerializer})
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(tags=swagger_tags,
                   responses={status.HTTP_204_NO_CONTENT: None})
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)
