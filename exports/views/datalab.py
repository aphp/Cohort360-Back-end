from django_filters import rest_framework as filters, OrderingFilter

from exports.models import Datalab
from exports.serializers import DatalabSerializer
from exports.views.base_viewset import ExportsBaseViewSet


class DatalabFilter(filters.FilterSet):
    ordering = OrderingFilter(fields=('created_datetime',))

    class Meta:
        model = Datalab
        fields = ('infrastructure_provider',)


class DatalabViewSet(ExportsBaseViewSet):
    serializer_class = DatalabSerializer
    queryset = Datalab.objects.all()
    swagger_tags = ['Exports - Datalab']
    filterset_class = DatalabFilter
    search_fields = ("infrastructure_provider__name",)
