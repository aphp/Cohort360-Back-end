from django_filters import rest_framework as filters, OrderingFilter

from exports.models import Datalab
from exports.permissions import ManageDatalabsPermission, ReadDatalabsPermission
from exports.serializers import DatalabSerializer
from exports.views.v1.base_viewset import ExportsBaseViewSet


class DatalabFilter(filters.FilterSet):
    ordering = OrderingFilter(fields=('created_datetime',))

    class Meta:
        model = Datalab
        fields = ('infrastructure_provider',)


class DatalabViewSet(ExportsBaseViewSet):
    serializer_class = DatalabSerializer
    queryset = Datalab.objects.all()
    swagger_tags = ['Exports - Datalabs']
    filterset_class = DatalabFilter
    search_fields = ("name", "infrastructure_provider__name")

    def get_permissions(self):
        if self.request.method in ['post', 'patch', 'delete']:
            return [ManageDatalabsPermission()]
        return [ReadDatalabsPermission()]
