from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from admin_cohort.models import MaintenancePhase, get_next_maintenance
from admin_cohort.permissions import MaintenancePermission
from admin_cohort.serializers import MaintenancePhaseSerializer


class MaintenancePhaseViewSet(viewsets.ModelViewSet):
    queryset = MaintenancePhase.objects.all()
    ordering_fields = ("start_datetime", "end_datetime")
    lookup_field = "id"
    search_fields = ["subject"]
    filterset_fields = ["subject", "start_datetime", "end_datetime"]
    http_method_names = ["get", "delete", "post", "patch"]
    permission_classes = (MaintenancePermission,)
    serializer_class = MaintenancePhaseSerializer

    @swagger_auto_schema(
        operation_description=(
                "Returns next maintenance if exists. Next maintenance is "
                "either: "
                "\n- the one currently active. If several, the one with "
                "the biggest end_datetime"
                "\n- if existing, and if no currently active, "
                "the one with smallest start_datetime that is bigger than now"),
        responses={200: openapi.Response(
            'There is a coming or current maintenance. '
            'The response can be null otherwise.', MaintenancePhaseSerializer)
        }
    )
    @action(methods=['get'], detail=False, url_path='next')
    def next(self, request, *args, **kwargs):
        q = get_next_maintenance()
        d = self.get_serializer(q).data if q is not None else {}
        return Response(d)
