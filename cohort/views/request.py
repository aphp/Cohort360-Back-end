from django.http import QueryDict
from django_filters import rest_framework as filters, OrderingFilter
from rest_framework.pagination import LimitOffsetPagination
from rest_framework_extensions.mixins import NestedViewSetMixin

from admin_cohort.cache_utils import cache_response, invalidate_cache
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
    swagger_tags = ["Cohort - requests"]
    pagination_class = LimitOffsetPagination
    filterset_class = RequestFilter
    search_fields = ("$name", "$description",)

    @cache_response()
    def list(self, request, *args, **kwargs):
        return super(RequestViewSet, self).list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        response = super(RequestViewSet, self).create(request, *args, **kwargs)
        invalidate_cache(view_instance=self, user=request.user)
        return response

    def update(self, request, *args, **kwargs):
        response = super(RequestViewSet, self).update(request, *args, **kwargs)
        invalidate_cache(view_instance=self, user=request.user)
        return response

    def destroy(self, request, *args, **kwargs):
        response = super(RequestViewSet, self).destroy(request, *args, **kwargs)
        invalidate_cache(view_instance=self, user=request.user)
        return response


class NestedRequestViewSet(RequestViewSet):

    def create(self, request, *args, **kwargs):
        if type(request.data) == QueryDict:
            request.data._mutable = True
        if 'parent_folder' in kwargs:
            request.data["parent_folder"] = kwargs['parent_folder']
        return super(NestedRequestViewSet, self).create(request, *args, **kwargs)
