from django.http import QueryDict
from django_filters import rest_framework as filters, OrderingFilter
from rest_framework.pagination import LimitOffsetPagination
from rest_framework_extensions.mixins import NestedViewSetMixin

from admin_cohort.views import SwaggerSimpleNestedViewSetMixin
from cohort.models import Request
from cohort.serializers import RequestSerializer
from cohort.views.utils import UserObjectsRestrictedViewSet


class RequestFilter(filters.FilterSet):
    ordering = OrderingFilter(fields=('name', 'created_at', 'modified_at',
                                      'favorite', 'data_type_of_query'))

    class Meta:
        model = Request
        fields = ('uuid', 'name', 'favorite', 'data_type_of_query',
                  'parent_folder', 'shared_by')


class RequestViewSet(NestedViewSetMixin, UserObjectsRestrictedViewSet):
    queryset = Request.objects.all()
    serializer_class = RequestSerializer
    http_method_names = ["get", "post", "patch", "delete"]
    lookup_field = "uuid"
    swagger_tags = ["Cohort - requests"]
    pagination_class = LimitOffsetPagination
    filterset_class = RequestFilter
    search_fields = ("$name", "$description",)


class NestedRequestViewSet(SwaggerSimpleNestedViewSetMixin, RequestViewSet):

    def create(self, request, *args, **kwargs):
        if type(request.data) == QueryDict:
            request.data._mutable = True
        if 'parent_folder' in kwargs:
            request.data["parent_folder"] = kwargs['parent_folder']
        return super(NestedRequestViewSet, self).create(request, *args, **kwargs)
