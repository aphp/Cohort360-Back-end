from django_filters import rest_framework as filters, OrderingFilter
from rest_framework.pagination import LimitOffsetPagination
from rest_framework_extensions.mixins import NestedViewSetMixin

from admin_cohort.cache_utils import cache_response, invalidate_cache
from admin_cohort.views import CustomLoggingMixin
from cohort.models import Folder
from cohort.serializers import FolderSerializer
from cohort.views.shared import UserObjectsRestrictedViewSet


class FolderFilter(filters.FilterSet):
    ordering = OrderingFilter(fields=('name', 'created_at', 'modified_at'))

    class Meta:
        model = Folder
        fields = ['uuid', 'name']


class FolderViewSet(CustomLoggingMixin, NestedViewSetMixin, UserObjectsRestrictedViewSet):
    queryset = Folder.objects.all()
    serializer_class = FolderSerializer
    http_method_names = ['get', 'post', 'patch', 'delete']
    lookup_field = "uuid"

    swagger_tags = ['Cohort - folders']
    logging_methods = ['POST', 'PUT', 'PATCH', 'DELETE']
    pagination_class = LimitOffsetPagination

    filterset_class = FolderFilter
    search_fields = ('$name',)

    @cache_response()
    def list(self, request, *args, **kwargs):
        return super(FolderViewSet, self).list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        response = super(FolderViewSet, self).create(request, *args, **kwargs)
        invalidate_cache(view_instance=self, user=request.user)
        return response

    def update(self, request, *args, **kwargs):
        response = super(FolderViewSet, self).update(request, *args, **kwargs)
        invalidate_cache(view_instance=self, user=request.user)
        return response

    def destroy(self, request, *args, **kwargs):
        response = super(FolderViewSet, self).destroy(request, *args, **kwargs)
        invalidate_cache(view_instance=self, user=request.user)
        return response
