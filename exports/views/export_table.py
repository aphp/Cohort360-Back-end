from django_filters import rest_framework as filters, OrderingFilter

from exports.models import ExportTable
from exports.serializers import ExportTableSerializer
from exports.views.base_viewset import ExportsBaseViewSet


class ExportTableFilter(filters.FilterSet):

    name = filters.DateTimeFilter(field_name="name", lookup_expr='icontains')
    export_name = filters.CharFilter(field_name="export__name", lookup_expr="icontains")
    cohort_result_subset_name = filters.CharFilter(field_name="cohort_result_subset__name", lookup_expr="icontains")
    filter_name = filters.CharFilter(field_name="filter__name", lookup_expr="icontains")
    ordering = OrderingFilter(fields=('name',))

    class Meta:
        model = ExportTable
        fields = ("name",
                  "export",
                  "export_name",
                  "cohort_result_subset",
                  "cohort_result_subset_name",
                  "filter",
                  "filter_name")


class ExportTableViewSet(ExportsBaseViewSet):
    serializer_class = ExportTableSerializer
    queryset = ExportTable.objects.all()
    swagger_tags = ['Exports - ExportTable']
    filterset_class = ExportTableFilter

