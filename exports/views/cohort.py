from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status

from admin_cohort.types import JobStatus
from cohort.models import CohortResult
from cohort.permissions import IsOwnerPermission
from exports.serializers import ExportsCohortResultSerializer
from exports.views import ExportsBaseViewSet


@extend_schema_view(
    retrieve=extend_schema(exclude=True),
    list=extend_schema(responses={status.HTTP_200_OK: ExportsCohortResultSerializer(many=True)}),
)
class CohortViewSet(ExportsBaseViewSet):
    queryset = CohortResult.objects.filter(request_job_status=JobStatus.finished,
                                           is_subset=False)
    http_method_names = ["get"]
    permission_classes = [IsOwnerPermission]
    serializer_class = ExportsCohortResultSerializer
    filterset_fields = ("owner_id",)
    swagger_tags = ['Exports - cohorts']
