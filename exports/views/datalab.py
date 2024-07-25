from django_filters import rest_framework as filters, OrderingFilter

from exports.models import Datalab
from exports.permissions import ManageDatalabsPermission, ReadDatalabsPermission
from exports.serializers import DatalabSerializer
from exports.views.base_viewset import ExportsBaseViewSet


class DatalabFilter(filters.FilterSet):
    ordering = OrderingFilter(fields=('created_at',
                                      'name'))

    class Meta:
        model = Datalab
        fields = ('name',
                  'infrastructure_provider',
                  'created_at')


class DatalabViewSet(ExportsBaseViewSet):
    serializer_class = DatalabSerializer
    queryset = Datalab.objects.all()
    swagger_tags = ['Exports - Datalabs']
    filterset_class = DatalabFilter
    http_method_names = ['get', 'post', 'patch']
    search_fields = ("name", "infrastructure_provider__name")

    def get_permissions(self):
        if self.request.method in ("POST", "PATCH"):
            return [ManageDatalabsPermission()]
        return [ReadDatalabsPermission()]

    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
