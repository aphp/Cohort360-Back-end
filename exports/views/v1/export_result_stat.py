from django_filters import rest_framework as filters, OrderingFilter

from exports.models import ExportResultStat
from exports.serializers import ExportResultStatSerializer
from exports.views.v1.base_viewset import ExportsBaseViewSet


class ExportResultStatFilter(filters.FilterSet):
    name = filters.DateTimeFilter(field_name="name", lookup_expr='icontains')
    export_name = filters.CharFilter(field_name="export__name", lookup_expr="icontains")
    ordering = OrderingFilter(fields=("name",
                                      "type",
                                      "value",
                                      ("export__name", "export")))

    class Meta:
        model = ExportResultStat
        fields = ("name",
                  "export",
                  "export_name",
                  "type")


class ExportResultStatViewSet(ExportsBaseViewSet):
    serializer_class = ExportResultStatSerializer
    queryset = ExportResultStat.objects.all()
    swagger_tags = ['Exports - ExportResultStat']
    filterset_class = ExportResultStatFilter
    http_method_names = ['get', 'post', 'patch']
