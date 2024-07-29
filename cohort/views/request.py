from django.http import QueryDict
from django_filters import rest_framework as filters, OrderingFilter
from rest_framework_extensions.mixins import NestedViewSetMixin

from admin_cohort.tools.cache import cache_response
from admin_cohort.tools.negative_limit_paginator import NegativeLimitOffsetPagination
from cohort.models import Request
from cohort.serializers import RequestSerializer
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
    pagination_class = NegativeLimitOffsetPagination
    filterset_class = RequestFilter
    search_fields = ("$name", "$description",)
    swagger_tags = ["Requests"]

    @cache_response()
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class NestedRequestViewSet(RequestViewSet):

    def create(self, request, *args, **kwargs):
        if type(request.data) is QueryDict:
            request.data._mutable = True
        if 'parent_folder' in kwargs:
            request.data["parent_folder"] = kwargs['parent_folder']
        return super().create(request, *args, **kwargs)
