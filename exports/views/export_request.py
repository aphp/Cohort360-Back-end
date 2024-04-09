import logging

from django.db import transaction
from django.db.models import Q
from django_filters import rest_framework as filters, OrderingFilter
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from admin_cohort.tools.cache import cache_response
from admin_cohort.tools import join_qs
from admin_cohort.tools.negative_limit_paginator import NegativeLimitOffsetPagination
from admin_cohort.tools.request_log_mixin import RequestLogMixin
from exports.models import ExportRequest
from exports.permissions import ExportRequestsPermission
from exports.serializers import ExportRequestSerializer, ExportRequestListSerializer
from exports.exceptions import BadRequestError, FilesNoLongerAvailable, StorageProviderException
from exports.services.export_request import export_request_service

_logger = logging.getLogger('django.request')


class ExportRequestFilter(filters.FilterSet):

    def multi_fields_filter(self, queryset, field, value: str):
        if value:
            return queryset.filter(join_qs([Q(cohort_fk__owner__firstname__icontains=value),
                                            Q(cohort_fk__owner__lastname__icontains=value)]))
        return queryset

    def multi_value_filter(self, queryset, field, value: str):
        if value:
            sub_values = [val.strip() for val in value.split(",")]
            return queryset.filter(join_qs([Q(**{field: v}) for v in sub_values]))
        return queryset

    cohort_name = filters.CharFilter(field_name="cohort_fk__name", lookup_expr='icontains')
    insert_datetime_gte = filters.DateTimeFilter(field_name="insert_datetime", lookup_expr='gte')
    insert_datetime_lte = filters.DateTimeFilter(field_name="insert_datetime", lookup_expr='lte')
    cohort_owner = filters.CharFilter(method="multi_fields_filter")
    output_format = filters.CharFilter(method="multi_value_filter", field_name="output_format")
    request_job_status = filters.CharFilter(method="multi_value_filter", field_name="request_job_status")

    ordering = OrderingFilter(fields=('insert_datetime',
                                      'output_format',
                                      ('owner__firstname', 'owner')))

    class Meta:
        model = ExportRequest
        fields = ('output_format', 'request_job_status', 'cohort_name', 'cohort_owner',
                  'creator_fk', 'target_unix_account', 'insert_datetime', 'owner')


class ExportRequestViewSet(RequestLogMixin, viewsets.ModelViewSet):
    queryset = ExportRequest.objects.all()
    serializer_class = ExportRequestSerializer
    lookup_field = "id"
    permission_classes = [ExportRequestsPermission]
    swagger_tags = ['Exports']
    pagination_class = NegativeLimitOffsetPagination
    filterset_class = ExportRequestFilter
    http_method_names = ['get', 'post']
    logging_methods = ['POST']
    search_fields = ("owner__username", "owner__firstname", "owner__lastname",
                     "cohort_id", "cohort_fk__name", "request_job_status", "output_format",
                     "target_name", "target_unix_account__name")

    def should_log(self, request, response):
        return super().should_log(request, response) or self.action == "download"

    def get_serializer_context(self):
        return {'request': self.request}

    @swagger_auto_schema(responses={'200': openapi.Response("List of export requests", ExportRequestListSerializer()),
                                    '204': openapi.Response("HTTP_204 if no export requests found")})
    @cache_response()
    def list(self, request, *args, **kwargs):
        q = self.filter_queryset(self.queryset)
        page = self.paginate_queryset(q)
        if page:
            serializer = ExportRequestListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(
        request_body=openapi.Schema(type=openapi.TYPE_OBJECT,
                                    properties={'motivation': openapi.Schema(type=openapi.TYPE_STRING),
                                                'output_format': openapi.Schema(type=openapi.TYPE_STRING,
                                                                                description="hive, csv (default)"),
                                                'cohort_id': openapi.Schema(type=openapi.TYPE_STRING,
                                                                            description="use cohort_fk instead"),
                                                'provider_source_value': openapi.Schema(type=openapi.TYPE_STRING),
                                                'target_unix_account': openapi.Schema(type=openapi.TYPE_INTEGER),
                                                'tables': openapi.Schema(type=openapi.TYPE_ARRAY,
                                                                         items=openapi.Schema(
                                                                             type=openapi.TYPE_OBJECT,
                                                                             properties={
                                                                                 'omop_table_name': openapi.Schema(
                                                                                     type=openapi.TYPE_STRING)})),
                                                'nominative': openapi.Schema(type=openapi.TYPE_BOOLEAN,
                                                                             description="Default at False"),
                                                'shift_dates': openapi.Schema(type=openapi.TYPE_BOOLEAN,
                                                                              description="Default at False"),
                                                'cohort_fk': openapi.Schema(type=openapi.TYPE_STRING,
                                                                            description="Pk for a CohortResult"),
                                                'provider_id': openapi.Schema(type=openapi.TYPE_STRING,
                                                                              description='Deprecated'),
                                                'owner': openapi.Schema(type=openapi.TYPE_STRING,
                                                                        description="Pk for user that will receive the "
                                                                                    "export. WIll be set to the "
                                                                                    "request creator if undefined.")
                                                },
                                    required=["tables"]))
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        export_request_service.validate_export_data(data=request.data, owner=request.user)
        tables = request.data.pop("tables", [])
        response = super().create(request, *args, **kwargs)
        transaction.on_commit(lambda: export_request_service.proceed_with_export(export=response.data.serializer.instance,
                                                                                 tables=tables))
        return response

    @action(detail=True, methods=['get'], url_path="download")
    def download(self, request, *args, **kwargs):
        try:
            return export_request_service.download(export=self.get_object())
        except (BadRequestError, FilesNoLongerAvailable) as e:
            return Response(data=f"Error downloading files: {e}", status=status.HTTP_400_BAD_REQUEST)
        except StorageProviderException as e:
            return Response(data=f"Storage provider error: {e}", status=status.HTTP_500_INTERNAL_SERVER_ERROR)
