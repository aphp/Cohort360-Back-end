from django_filters import rest_framework as filters, OrderingFilter

from cohort.models import RequestRefreshSchedule
from cohort.serializers import RequestRefreshScheduleSerializer
from cohort.services.request import requests_service
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

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        requests_service.create_refresh_schedule(refresh_schedule=request.data.serializer.instance)
        return response

    def partial_update(self, request, *args, **kwargs):
        response = super().partial_update(request, *args, **kwargs)
        requests_service.update_refresh_schedule(refresh_schedule=self.get_object())
        return response
