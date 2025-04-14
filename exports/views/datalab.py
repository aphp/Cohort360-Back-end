from django_filters import rest_framework as filters, OrderingFilter
from rest_framework.pagination import PageNumberPagination

from exports.models import Datalab
from exports.permissions import ManageDatalabsPermission, ReadDatalabsPermission
from exports.serializers import DatalabSerializer
from exports.views import ExportsBaseViewSet


class DatalabFilter(filters.FilterSet):
    infra_provider = filters.CharFilter(field_name='infrastructure_provider__name', lookup_expr='icontains')
    ordering = OrderingFilter(fields=('created_at',
                                      'name'))

    class Meta:
        model = Datalab
        fields = ('name',
                  'infra_provider',)


class DatalabViewSet(ExportsBaseViewSet):
    serializer_class = DatalabSerializer
    queryset = Datalab.objects.all()
    swagger_tags = ['Exports - Datalabs']
    filterset_class = DatalabFilter
    http_method_names = ['get', 'post', 'patch']
    search_fields = ("name", "infrastructure_provider__name")
    pagination_class = PageNumberPagination

    def get_permissions(self):
        if self.request.method in ("POST", "PATCH"):
            return [ManageDatalabsPermission()]
        return [ReadDatalabsPermission()]
