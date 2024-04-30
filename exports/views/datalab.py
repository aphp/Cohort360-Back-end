from django_filters import rest_framework as filters, OrderingFilter
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

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

    @swagger_auto_schema(manual_parameters=list(map(lambda x: openapi.Parameter(in_=openapi.IN_QUERY, name=x[0], description=x[1], type=x[2]),
                                                    [["search", f"Search within multiple fields: {','.join(search_fields)}", openapi.TYPE_STRING],
                                                     ["ordering", "`name` or `created_at`. Prepend '-' for desc order", openapi.TYPE_STRING]])))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
