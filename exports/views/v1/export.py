from django.db.models import Q
from django_filters import rest_framework as filters, OrderingFilter

from admin_cohort.tools import join_qs
from exports.models import Export
from exports.permissions import CSVExportPermission, JupyterExportPermission
from exports.serializers import ExportSerializer
from exports.types import ExportType
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
    search_fields = ("name",
                     "owner__provider_username",
                     "owner__firstname",
                     "owner__lastname",
                     "request_job_status",
                     "output_format",
                     "target_name",
                     "target_unix_account__name")

    def get_permissions(self):
        permissions = {ExportType.CSV.name: CSVExportPermission,
                       ExportType.HIVE.name: JupyterExportPermission
                       }
        if self.request.method in ("POST", "PATCH", "DELETE"):
            permission = permissions.get(self.request.data.get("output_format"))
            if permission:
                return [permission()]
            raise ValueError("Invalid `output_format` was provided")
        return super().get_permissions()
