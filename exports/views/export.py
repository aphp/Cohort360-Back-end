import json
import logging

from django.db import transaction
from django.db.models import Q
from django.db.models.expressions import Subquery, OuterRef
from django.http.response import HttpResponse
from django_filters import rest_framework as filters, OrderingFilter
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter, PolymorphicProxySerializer
from requests.exceptions import RequestException
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from admin_cohort.tools import join_qs
from admin_cohort.tools.cache import cache_response
from admin_cohort.tools.request_log_mixin import RequestLogMixin
from admin_cohort.types import JobStatus
from exports.exceptions import FilesNoLongerAvailable, BadRequestError, StorageProviderException
from exports.models import Export, ExportTable
from exports.permissions import ExportPermission, RetryExportPermission, ExportLogsPermission
from exports.serializers import ExportSerializer, ExportsListSerializer, ExportCreateSerializer
from exports.services.export import export_service
from exports.views import ExportsBaseViewSet

_logger = logging.getLogger("django.request")


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
    motivation = filters.CharFilter(field_name="motivation", lookup_expr='icontains')
    ordering = OrderingFilter(fields=('created_at',
                                      'modified_at',
                                      'output_format',
                                      ('request_job_status', 'status'),
                                      'patients_count',
                                      ('owner__firstname', 'owner')))

    class Meta:
        model = Export
        fields = ("motivation",
                  "output_format",
                  "status",
                  "owner")


class ExportViewSet(RequestLogMixin, ExportsBaseViewSet):
    export_table_subquery = ExportTable.objects.filter(export_id=OuterRef('uuid'),
                                                       cohort_result_source__isnull=False) \
        .values('cohort_result_source__name',
                'cohort_result_source__group_id',
                'cohort_result_source__dated_measure__measure'
                )[:1]
    queryset = Export.objects.prefetch_related('export_tables__cohort_result_source__dated_measure') \
        .annotate(cohort_name=Subquery(export_table_subquery.values('cohort_result_source__name')),
                  cohort_id=Subquery(export_table_subquery.values('cohort_result_source__group_id')),
                  patients_count=Subquery(export_table_subquery.values('cohort_result_source__dated_measure__measure')))
    serializer_class = ExportSerializer
    permission_classes = [ExportPermission]
    swagger_tags = ['Exports']
    filterset_class = ExportFilter
    http_method_names = ['get', 'post']
    logging_methods = ['POST']
    search_fields = ("owner__username",
                     "owner__firstname",
                     "owner__lastname",
                     "motivation",
                     "request_job_status",
                     "output_format",
                     "target_name",
                     "datalab__name",
                     "cohort_name",
                     "cohort_id")

    def get_permissions(self):
        if self.action == self.retry.__name__ or self.action == self.relaunch.__name__:
            return [RetryExportPermission()]
        if self.action == self.logs.__name__:
            return [ExportLogsPermission()]
        return super().get_permissions()

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
            _logger.error(f"Export creation: Bad request - {ve}")
            return Response(data=ve.detail, status=status.HTTP_400_BAD_REQUEST)
        tables = request.data.pop("export_tables", [])
        response = super().create(request, *args, **kwargs)
        try:
            transaction.on_commit(lambda: export_service.proceed_with_export(export=response.data.serializer.instance,
                                                                             tables=tables,
                                                                             http_request=request))
        except ValidationError as ve:
            return Response(data=ve.detail, status=status.HTTP_400_BAD_REQUEST)
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

    @extend_schema(responses={status.HTTP_200_OK: OpenApiTypes.STR})
    @action(detail=True, methods=['post'], url_path="retry")
    def retry(self, request, *args, **kwargs):
        export = self.get_object()
        export_service.retry(export=export)
        return Response(data=f"The export `{export.uuid}` has been relaunched", status=status.HTTP_200_OK)

    @extend_schema(responses={status.HTTP_201_CREATED: ExportSerializer})
    @action(detail=True, methods=['post'], url_path="relaunch")
    @transaction.atomic
    def relaunch(self, request, *args, **kwargs):
        """
        Copy an existing export and create a new one with the same configuration
        """
        original_export = self.get_object()
        # Build export data from the original export
        export_data = {
            "motivation": original_export.motivation,
            "nominative": original_export.nominative,
            "shift_date": original_export.shift_dates,
            "output_format": original_export.output_format,
            "group_tables": original_export.group_tables,
        }
        if original_export.datalab:
            export_data["datalab"] = original_export.datalab.pk

        # Build export_tables data from original export tables
        tables = []
        for table in original_export.export_tables.all():
            table_data = {
                "table_name": table.name,
                "respect_table_relationships": table.respect_table_relationships,
            }
            if table.cohort_result_source:
                table_data["cohort_result_source"] = str(table.cohort_result_source.uuid)
            if table.fhir_filter:
                table_data["fhir_filter"] = str(table.fhir_filter.uuid)
            if table.columns:
                table_data["columns"] = table.columns
            else:
                table_data["columns"] = None
            if table.pivot_merge:
                table_data["pivot_merge"] = table.pivot_merge
            if table.pivot_merge_columns:
                table_data["pivot_merge_columns"] = table.pivot_merge_columns
            if table.pivot_merge_ids:
                table_data["pivot_merge_ids"] = table.pivot_merge_ids

            tables.append(table_data)

        export_data["export_tables"] = tables
        # Remove export_tables from data before creating Export model
        tables_to_create = export_data.pop("export_tables", [])

        # Create serializer and save
        serializer = ExportSerializer(data=export_data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save(owner=original_export.owner)
        # Proceed with export processing asynchronously
        try:
            transaction.on_commit(lambda: export_service.proceed_with_export(
                export=serializer.instance,
                tables=tables_to_create,
                http_request=request
            ))
        except ValidationError as ve:
            return Response(data=ve.detail, status=status.HTTP_400_BAD_REQUEST)

        return Response(data=serializer.data, status=status.HTTP_201_CREATED)

    @extend_schema(responses={(status.HTTP_200_OK, "application/json"): OpenApiTypes.BINARY})
    @action(detail=True, methods=['get'], url_path="logs")
    def logs(self, request, *args, **kwargs):
        export = self.get_object()
        if export.request_job_status == JobStatus.finished:
            return Response(data="No logs available. The target export has finished successfully",
                            status=status.HTTP_200_OK)
        if not export.request_job_id:
            return Response(data="The target export has no job ID", status=status.HTTP_400_BAD_REQUEST)
        try:
            logs_data = export_service.get_execution_logs(export=export)
            response = HttpResponse(json.dumps(logs_data, indent=4), content_type='application/json',
                                    status=status.HTTP_200_OK)
            response['Content-Disposition'] = f'attachment; filename="logs_export_{export.target_name}.json"'
            return response
        except TimeoutError:
            return Response(data="Timeout while fetching logs. Please try again later.",
                            status=status.HTTP_408_REQUEST_TIMEOUT)
        except RequestException as e:
            return Response(data=f"Error fetching logs: {e}", status=status.HTTP_500_INTERNAL_SERVER_ERROR)
