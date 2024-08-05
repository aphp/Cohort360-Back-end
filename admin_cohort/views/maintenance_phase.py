from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from admin_cohort.models import MaintenancePhase
from admin_cohort.services.maintenance import maintenance_service
from admin_cohort.permissions import MaintenancesPermission
from admin_cohort.serializers import MaintenancePhaseSerializer

extended_schema = extend_schema(tags=["Maintenance"])


@extend_schema_view(
    list=extend_schema(exclude=True),
    retrieve=extended_schema,
    create=extended_schema,
    partial_update=extended_schema,
    destroy=extended_schema,
    next=extended_schema
)
class MaintenancePhaseViewSet(viewsets.ModelViewSet):
    queryset = MaintenancePhase.objects.all()
    serializer_class = MaintenancePhaseSerializer
    lookup_field = "id"
    search_fields = ["$subject"]
    filterset_fields = ["subject", "start_datetime", "end_datetime"]
    http_method_names = ["get", "delete", "post", "patch"]
    permission_classes = (MaintenancesPermission,)

    @action(methods=['get'], detail=False, url_path='next')
    def next(self, request, *args, **kwargs):
        q = maintenance_service.get_next_maintenance()
        d = self.get_serializer(q).data if q is not None else {}
        return Response(d)
