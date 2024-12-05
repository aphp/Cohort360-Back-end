import json

from django.db import transaction
from django.db.models import Q
from django_filters import rest_framework as filters, OrderingFilter
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter, PolymorphicProxySerializer
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from admin_cohort.tools import join_qs
from admin_cohort.tools.cache import cache_response
from admin_cohort.tools.request_log_mixin import RequestLogMixin
from exports.exceptions import FilesNoLongerAvailable, BadRequestError, StorageProviderException
from exports.models import Export
from exports.permissions import ExportPermission
from exports.serializers import ExportSerializer, ExportsListSerializer, ExportCreateSerializer
from exports.services.export import export_service
from exports.views import ExportsBaseViewSet


class ExportFilter(filters.FilterSet):

    def multi_value_filter(self, queryset, field, value: str):
        if value:
            sub_values = [val.strip() for val in value.split(",")]
            return queryset.filter(join_qs([Q(**{field: v}) for v in sub_values]))
        return queryset

    def owner_filter(self, queryset, field, value: str):
        if value:
            search_fields = ["username", "firstname", "lastname"]
            return queryset.filter(join_qs([Q(**{f"{field}__{f}__icontains": value}) for f in search_fields]))
        return queryset

    output_format = filters.CharFilter(method="multi_value_filter", field_name="output_format")
    status = filters.CharFilter(method="multi_value_filter", field_name="request_job_status")
    owner = filters.CharFilter(method="owner_filter", field_name="owner")
    motivation = filters.DateTimeFilter(field_name="motivation", lookup_expr='icontains')
    ordering = OrderingFilter(fields=('created_at',
                                      'output_format',
                                      'status',
                                      ('owner__firstname', 'owner')))

    class Meta:
        model = Export
        fields = ("motivation",
                  "output_format",
                  "status",
                  "owner")


class ExportViewSet(RequestLogMixin, ExportsBaseViewSet):
    serializer_class = ExportSerializer
    queryset = Export.objects.all()
    permission_classes = [ExportPermission]
    swagger_tags = ['Exports']
    filterset_class = ExportFilter
    http_method_names = ['get', 'post']
    logging_methods = ['POST']
    search_fields = ("owner__username",
                     "owner__firstname",
                     "owner__lastname",
                     "request_job_status",
                     "output_format",
                     "target_name",
                     "datalab__name")

    def should_log(self, request, response):
        return super().should_log(request, response) or self.action == self.download.__name__

    @extend_schema(parameters=[OpenApiParameter("return_full_objects", OpenApiTypes.BOOL)],
                   responses={status.HTTP_200_OK: PolymorphicProxySerializer(
                       component_name="", many=True, resource_type_field_name=None,
                       serializers=[ExportSerializer, ExportsListSerializer])})
    @cache_response()
    def list(self, request, *args, **kwargs):
        q = self.filter_queryset(self.queryset)
        page = self.paginate_queryset(q)
        return_full_objects = json.loads(request.query_params.get("return_full_objects", "false"))
        serializer = ExportsListSerializer
        if return_full_objects:
            serializer = ExportSerializer
        if page:
            serializer = serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(request=ExportCreateSerializer,
                   responses={status.HTTP_201_CREATED: ExportSerializer})
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        try:
            export_service.validate_export_data(data=request.data, owner=request.user)
        except ValidationError as ve:
            return Response(data=ve.detail, status=status.HTTP_400_BAD_REQUEST)
        tables = request.data.pop("export_tables", [])
        response = super().create(request, *args, **kwargs)
        transaction.on_commit(lambda: export_service.proceed_with_export(export=response.data.serializer.instance,
                                                                         tables=tables,
                                                                         http_request=request))
        return response


    @extend_schema(responses={(status.HTTP_200_OK, "application/zip"): OpenApiTypes.BINARY})
    @action(detail=True, methods=['get'], url_path="download")
    def download(self, request, *args, **kwargs):
        try:
            return export_service.download(export=self.get_object())
        except (BadRequestError, FilesNoLongerAvailable) as e:
            return Response(data=f"Error downloading files: {e}", status=status.HTTP_400_BAD_REQUEST)
        except StorageProviderException as e:
            return Response(data=f"Storage provider error: {e}", status=status.HTTP_500_INTERNAL_SERVER_ERROR)
