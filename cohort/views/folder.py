from django_filters import rest_framework as filters, OrderingFilter
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status
from rest_framework_extensions.mixins import NestedViewSetMixin

from admin_cohort.tools.cache import cache_response
from cohort.models import Folder
from cohort.serializers import FolderSerializer, FolderCreateSerializer, FolderPatchSerializer
from cohort.views.shared import UserObjectsRestrictedViewSet


class FolderFilter(filters.FilterSet):
    ordering = OrderingFilter(fields=('name', 'created_at', 'modified_at'))

    class Meta:
        model = Folder
        fields = []


@extend_schema_view(
    retrieve=extend_schema(responses={status.HTTP_200_OK: FolderSerializer}),
    list=extend_schema(responses={status.HTTP_200_OK: FolderSerializer(many=True)}),
    create=extend_schema(request=FolderCreateSerializer,
                         responses={status.HTTP_201_CREATED: FolderSerializer}),
    partial_update=extend_schema(request=FolderPatchSerializer,
                                 responses={status.HTTP_200_OK: FolderSerializer}),
    destroy=extend_schema(responses={status.HTTP_204_NO_CONTENT: None})
)
class FolderViewSet(NestedViewSetMixin, UserObjectsRestrictedViewSet):
    queryset = Folder.objects.all()
    serializer_class = FolderSerializer
    http_method_names = ['get', 'post', 'patch', 'delete']
    filterset_class = FolderFilter
    search_fields = ('$name',)
    swagger_tags = ['Folders']

    @cache_response()
    def list(self, request, *args, **kwargs):
        return super(FolderViewSet, self).list(request, *args, **kwargs)
