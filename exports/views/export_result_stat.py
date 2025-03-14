from django_filters import rest_framework as filters, OrderingFilter

from exports.models import ExportResultStat
from exports.serializers import ExportResultStatSerializer
from exports.views import ExportsBaseViewSet


class ExportResultStatFilter(filters.FilterSet):
    name = filters.DateTimeFilter(field_name="name", lookup_expr='icontains')
    export_target_name = filters.CharFilter(field_name="export__target_name", lookup_expr="icontains")
    ordering = OrderingFilter(fields=("name",
                                      "type",
                                      "value",
                                      ("export__target_name", "export")))

    class Meta:
        model = ExportResultStat
        fields = ("name",
                  "export",
                  "export_target_name",
                  "type")


class ExportResultStatViewSet(ExportsBaseViewSet):
    serializer_class = ExportResultStatSerializer
    queryset = ExportResultStat.objects.all()
    swagger_tags = ['Exports - Export Stats']
    filterset_class = ExportResultStatFilter
    http_method_names = ['get', 'post', 'patch']
