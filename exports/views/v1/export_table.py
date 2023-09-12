from django_filters import rest_framework as filters, OrderingFilter

from exports.models import ExportTable
from exports.serializers import ExportTableSerializer
from exports.views.v1.base_viewset import ExportsBaseViewSet


class ExportTableFilter(filters.FilterSet):

    name = filters.DateTimeFilter(field_name="name", lookup_expr='icontains')
    export_name = filters.CharFilter(field_name="export__name", lookup_expr="icontains")
    cohort_result_subset_name = filters.CharFilter(field_name="cohort_result_subset__name", lookup_expr="icontains")
    filter_name = filters.CharFilter(field_name="fhir_filter__name", lookup_expr="icontains")
    ordering = OrderingFilter(fields=('name',))

    class Meta:
        model = ExportTable
        fields = ("name",
                  "export",
                  "export_name",
                  "cohort_result_subset",
                  "cohort_result_subset_name",
                  "fhir_filter",
                  "filter_name")


class ExportTableViewSet(ExportsBaseViewSet):
    serializer_class = ExportTableSerializer
    queryset = ExportTable.objects.all()
    http_method_names = ["get"]
    swagger_tags = ['Exports - Export Tables']
    filterset_class = ExportTableFilter

