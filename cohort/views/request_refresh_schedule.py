from django_filters import rest_framework as filters, OrderingFilter
from drf_spectacular.utils import extend_schema
from rest_framework import status

from cohort.models import RequestRefreshSchedule
from cohort.serializers import RequestRefreshScheduleSerializer
from cohort.services.request_refresh_schedule import requests_refresher_service
from cohort.views.shared import UserObjectsRestrictedViewSet


class RequestRefreshScheduleFilter(filters.FilterSet):
    ordering = OrderingFilter(fields=('created_at', 'modified_at'))

    class Meta:
        model = RequestRefreshSchedule
        fields = ('request_snapshot_id',
                  'refresh_time',
                  'refresh_frequency')


class RequestRefreshScheduleViewSet(UserObjectsRestrictedViewSet):
    queryset = RequestRefreshSchedule.objects.all()
    lookup_field = "uuid"
    serializer_class = RequestRefreshScheduleSerializer
    http_method_names = ['get', 'post', 'patch', 'delete']
    filterset_class = RequestRefreshScheduleFilter
    swagger_tags = ['Cohort - Refresh Schedules']

    @extend_schema(responses={status.HTTP_201_CREATED: RequestRefreshScheduleSerializer})
    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        requests_refresher_service.create_refresh_schedule(http_request=request,
                                                           refresh_schedule=response.data.serializer.instance)
        return response

    @extend_schema(responses={status.HTTP_200_OK: RequestRefreshScheduleSerializer})
    def partial_update(self, request, *args, **kwargs):
        response = super().partial_update(request, *args, **kwargs)
        requests_refresher_service.reset_schedule_crontab(refresh_schedule=self.get_object())
        return response
