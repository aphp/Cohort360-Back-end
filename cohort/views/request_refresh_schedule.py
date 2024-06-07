from django_filters import rest_framework as filters, OrderingFilter

from cohort.models import RequestRefreshSchedule
from cohort.serializers import RequestRefreshScheduleSerializer
from cohort.views.shared import UserObjectsRestrictedViewSet


class RequestRefreshScheduleFilter(filters.FilterSet):
    ordering = OrderingFilter(fields=('created_at', 'modified_at'))

    class Meta:
        model = RequestRefreshSchedule
        fields = ('request',
                  'owner')


class RequestRefreshScheduleViewSet(UserObjectsRestrictedViewSet):
    queryset = RequestRefreshSchedule.objects.all()
    lookup_field = "uuid"
    serializer_class = RequestRefreshScheduleSerializer
    http_method_names = ['get', 'post', 'patch']
    filterset_class = RequestRefreshScheduleFilter
    swagger_tags = ['Cohort - request-refresh-schedule']
