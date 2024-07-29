from django_filters import rest_framework as filters, OrderingFilter

from admin_cohort.types import JobStatus
from cohort.models import CohortResult
from cohort.permissions import IsOwnerPermission
from exports.serializers import AnnexeCohortResultSerializer
from exports.views import ExportsBaseViewSet


class CohortFilter(filters.FilterSet):
    ordering = OrderingFilter(fields=('name', 'created_at'))

    class Meta:
        model = CohortResult
        fields = ('owner_id',)


class CohortViewSet(ExportsBaseViewSet):
    queryset = CohortResult.objects.filter(request_job_status=JobStatus.finished,
                                           is_subset=False)
    http_method_names = ["get"]
    permission_classes = [IsOwnerPermission]
    serializer_class = AnnexeCohortResultSerializer
    filterset_class = CohortFilter
    search_fields = ('$name', '$description')
    swagger_tags = ['Exports - cohorts']
