from django_filters import rest_framework as filters, OrderingFilter

from exports.models import InfrastructureProvider
from exports.serializers import InfrastructureProviderSerializer
from exports.views.base_viewset import ExportsBaseViewSet


class InfrastructureProviderFilter(filters.FilterSet):
    ordering = OrderingFilter(fields=('name',))

    class Meta:
        model = InfrastructureProvider
        fields = "__all__"


class InfrastructureProviderViewSet(ExportsBaseViewSet):
    serializer_class = InfrastructureProviderSerializer
    queryset = InfrastructureProvider.objects.all()
    swagger_tags = ['Exports - InfrastructureProvider']
    filterset_class = InfrastructureProviderFilter
    search_fields = ("infrastructure_provider__name",)

