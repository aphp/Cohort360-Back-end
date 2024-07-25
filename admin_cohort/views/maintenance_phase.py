from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from admin_cohort.models import MaintenancePhase
from admin_cohort.services.maintenance import maintenance_service
from admin_cohort.permissions import MaintenancesPermission
from admin_cohort.serializers import MaintenancePhaseSerializer


class MaintenancePhaseViewSet(viewsets.ModelViewSet):
    queryset = MaintenancePhase.objects.all()
    ordering_fields = ("start_datetime", "end_datetime")
    lookup_field = "id"
    search_fields = ["subject"]
    filterset_fields = ["subject", "start_datetime", "end_datetime"]
    http_method_names = ["get", "delete", "post", "patch"]
    permission_classes = (MaintenancesPermission,)
    serializer_class = MaintenancePhaseSerializer

    @action(methods=['get'], detail=False, url_path='next')
    def next(self, request, *args, **kwargs):
        q = maintenance_service.get_next_maintenance()
        d = self.get_serializer(q).data if q is not None else {}
        return Response(d)
