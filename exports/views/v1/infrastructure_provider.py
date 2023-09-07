from django_filters import rest_framework as filters, OrderingFilter

from exports.models import InfrastructureProvider
from exports.permissions import ManageDatalabsPermission, ReadDatalabsPermission
from exports.serializers import InfrastructureProviderSerializer
from exports.views.v1.base_viewset import ExportsBaseViewSet


class InfrastructureProviderFilter(filters.FilterSet):
    ordering = OrderingFilter(fields=('name',))

    class Meta:
        model = InfrastructureProvider
        fields = "__all__"


class InfrastructureProviderViewSet(ExportsBaseViewSet):
    serializer_class = InfrastructureProviderSerializer
    queryset = InfrastructureProvider.objects.all()
    swagger_tags = ['Exports - Infrastructure Providers']
    filterset_class = InfrastructureProviderFilter
    search_fields = ("infrastructure_provider__name",)

    def get_permissions(self):
        if self.request.method in ['post', 'patch', 'delete']:
            return [ManageDatalabsPermission()]
        return [ReadDatalabsPermission()]

