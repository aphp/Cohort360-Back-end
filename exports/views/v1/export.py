from django.db.models import Q
from django_filters import rest_framework as filters, OrderingFilter
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from admin_cohort.permissions import either
from admin_cohort.tools import join_qs
from exports.models import Export
from exports.permissions import CSVExportsPermission, JupyterExportPermission
from exports.serializers import ExportSerializer
from exports.services.export import export_service
from exports.views.v1.base_viewset import ExportsBaseViewSet


class ExportFilter(filters.FilterSet):

    def multi_value_filter(self, queryset, field, value: str):
        if value:
            sub_values = [val.strip() for val in value.split(",")]
            return queryset.filter(join_qs([Q(**{field: v}) for v in sub_values]))
        return queryset

    output_format = filters.CharFilter(method="multi_value_filter", field_name="output_format")
    status = filters.CharFilter(method="multi_value_filter", field_name="status")
    name = filters.DateTimeFilter(field_name="name", lookup_expr='icontains')
    motivation = filters.DateTimeFilter(field_name="motivation", lookup_expr='icontains')
    ordering = OrderingFilter(fields=('name',
                                      'insert_datetime',
                                      'output_format',
                                      'status',
                                      ('owner__firstname', 'owner')))

    class Meta:
        model = Export
        fields = ("name",
                  "motivation",
                  "output_format",
                  "status",
                  "owner")


class ExportViewSet(ExportsBaseViewSet):
    serializer_class = ExportSerializer
    queryset = Export.objects.all()
    swagger_tags = ['Exports - Exports']
    filterset_class = ExportFilter
    http_method_names = ['get', 'post', 'patch']
    search_fields = ("name",
                     "owner__username",
                     "owner__firstname",
                     "owner__lastname",
                     "request_job_status",
                     "output_format",
                     "target_name",
                     "target_unix_account__name")

    def get_permissions(self):
        if self.request.method in ("POST", "PATCH"):
            return either(CSVExportsPermission(), JupyterExportPermission())
        return super().get_permissions()

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={'output_format': openapi.Schema(type=openapi.TYPE_STRING, description="hive, csv (default)"),
                        'datalab': openapi.Schema(type=openapi.TYPE_STRING),
                        'nominative': openapi.Schema(type=openapi.TYPE_BOOLEAN, description="Defaults to False"),
                        'shift_dates': openapi.Schema(type=openapi.TYPE_BOOLEAN, description="Defaults to False"),
                        'export_tables': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(type=openapi.TYPE_OBJECT,
                                                 properties={'table_ids': openapi.Schema(type=openapi.TYPE_ARRAY,
                                                                                         items=openapi.Schema(type=openapi.TYPE_STRING)),
                                                             'respect_table_relationships': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                                                             'fhir_filter': openapi.Schema(type=openapi.TYPE_STRING),
                                                             'cohort_result_source': openapi.Schema(type=openapi.TYPE_STRING)}))}))
    def create(self, request, *args, **kwargs):
        export_service.process_export_creation(data=request.data, owner=request.user)
        export_tables = request.data.pop("export_tables", [])
        response = super().create(request, *args, **kwargs)
        export_service.create_tables(export_id=response.data["uuid"],
                                     export_tables=export_tables,
                                     http_request=request)
        return response
