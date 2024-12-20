from django_filters import rest_framework as filters, OrderingFilter

from exports.models import InfrastructureProvider
from exports.permissions import ManageDatalabsPermission, ReadDatalabsPermission
from exports.serializers import InfrastructureProviderSerializer
from exports.views import ExportsBaseViewSet


class InfrastructureProviderFilter(filters.FilterSet):
    ordering = OrderingFilter(fields=('name',))

    class Meta:
        model = InfrastructureProvider
        fields = ("name",)


class InfrastructureProviderViewSet(ExportsBaseViewSet):
    serializer_class = InfrastructureProviderSerializer
    queryset = InfrastructureProvider.objects.all()
    filterset_class = InfrastructureProviderFilter
    http_method_names = ['get', 'post', 'patch', 'delete']
    search_fields = ("$name",)
    swagger_tags = ['Exports - Infrastructure Providers']

    def get_permissions(self):
        if self.request.method in ("POST", "PATCH", "DELETE"):
            return [ManageDatalabsPermission()]
        return [ReadDatalabsPermission()]

