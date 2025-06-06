from django_filters import FilterSet, IsoDateTimeFilter, OrderingFilter
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from admin_cohort.models import MaintenancePhase
from admin_cohort.permissions import MaintenancesPermission, either
from admin_cohort.serializers import MaintenancePhaseSerializer
from admin_cohort.services.maintenance import maintenance_service
from cohort_job_server.permissions import AuthenticatedApplicativeUserPermission

extended_schema = extend_schema(tags=["Maintenance"])


class MaintenancePhaseFilter(FilterSet):
    min_start_datetime = IsoDateTimeFilter(field_name='start_datetime', lookup_expr='gte')
    max_end_datetime = IsoDateTimeFilter(field_name='end_datetime', lookup_expr='lte')

    ordering = OrderingFilter(fields=('start_datetime', 'end_datetime'))

    class Meta:
        model = MaintenancePhase
        fields = ['subject', 'start_datetime', 'end_datetime']


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
    filterset_class = MaintenancePhaseFilter
    http_method_names = ["get", "delete", "post", "patch"]

    def get_permissions(self):
        return either(MaintenancesPermission(),
                      AuthenticatedApplicativeUserPermission())

    @action(methods=['get'], detail=False, url_path='next')
    def next(self, request, *args, **kwargs):
        q = maintenance_service.get_next_maintenance()
        d = self.get_serializer(q).data if q is not None else {}
        return Response(d)

    def destroy(self, request, *args, **kwargs):
        maintenance_service.send_deleted_maintenance_notification(self.get_object())
        return super().destroy(request, *args, **kwargs)
