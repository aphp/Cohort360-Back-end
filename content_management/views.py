from django.utils import timezone
from drf_spectacular.utils import extend_schema_view, extend_schema
from django_filters.filters import OrderingFilter, CharFilter
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import FilterSet

from content_management.apps import ContentManagementConfig
from content_management.models import Content
from content_management.permissions import ContentManagementPermission
from content_management.serializers import ContentSerializer


class ContentFilter(FilterSet):
    content_type = CharFilter(method='filter_content_type')
    page_source = CharFilter(method='filter_page')

    class Meta:
        model = Content
        fields = ['content_type', 'page']

    def filter_content_type(self, queryset, name, value):
        if value:
            content_types = value.split(',')
            valid_types = set(ContentManagementConfig.CONTENT_TYPES.keys())
            valid_content_types = [ct for ct in content_types if ct in valid_types]
            if not valid_content_types:
                raise ValueError("Invalid content types provided")
            return queryset.filter(content_type__in=valid_content_types)
        return queryset

    def filter_page(self, queryset, name, value):
        if value:
            pages = value.split(',')
            return queryset.filter(page__in=pages)
        return queryset

    ordering = OrderingFilter(fields=('created_at',
                                      'modified_at',
                                      'title'))


extended_schema = extend_schema(tags=["Web Content"])


@extend_schema_view(
    list=extended_schema,
    retrieve=extended_schema,
    create=extended_schema,
    partial_update=extended_schema,
    destroy=extended_schema,
    content_types=extended_schema
)
class ContentViewSet(viewsets.ModelViewSet):
    permission_classes = [ContentManagementPermission]
    queryset = Content.objects.filter(deleted_at__isnull=True)
    serializer_class = ContentSerializer
    http_method_names = ["post", "get", "patch", "delete"]
    filterset_class = ContentFilter
    search_fields = ['$title', '$content']

    @action(detail=False, methods=['get'])
    def content_types(self, request):
        return Response(ContentManagementConfig.CONTENT_TYPES)

    def perform_destroy(self, instance):
        # Soft delete instead of hard delete
        instance.deleted_at = timezone.now()
        instance.save()
