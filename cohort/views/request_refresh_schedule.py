from django_filters import rest_framework as filters, OrderingFilter
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from cohort.models import RequestRefreshSchedule
from cohort.serializers import RequestRefreshScheduleSerializer
from cohort.services.request_refresh_schedule import requests_refresher_service
from cohort.views.shared import UserObjectsRestrictedViewSet


class RequestRefreshScheduleFilter(filters.FilterSet):
    ordering = OrderingFilter(fields=('created_at', 'modified_at'))

    class Meta:
        model = RequestRefreshSchedule
        fields = ('request_snapshot',)


class RequestRefreshScheduleViewSet(UserObjectsRestrictedViewSet):
    queryset = RequestRefreshSchedule.objects.all()
    lookup_field = "uuid"
    serializer_class = RequestRefreshScheduleSerializer
    http_method_names = ['get', 'post', 'patch', 'delete']
    filterset_class = RequestRefreshScheduleFilter
    swagger_tags = ['Cohort - Refresh Schedules']

    @swagger_auto_schema(request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={"request_snapshot_id": openapi.Schema(type=openapi.TYPE_STRING),
                    "refresh_time": openapi.Schema(type=openapi.TYPE_STRING),
                    "refresh_frequency": openapi.Schema(type=openapi.TYPE_STRING)},
        required=["request_snapshot_id", "refresh_time", "refresh_frequency"]),
        responses={'201': openapi.Response("Refresh Schedule created", RequestRefreshScheduleSerializer()),
                   '400': openapi.Response("Bad Request")})
    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        requests_refresher_service.create_refresh_schedule(http_request=request,
                                                           refresh_schedule=response.data.serializer.instance)
        return response

    @swagger_auto_schema(request_body=openapi.Schema(
                             type=openapi.TYPE_OBJECT,
                             properties={"refresh_time": openapi.Schema(type=openapi.TYPE_STRING),
                                         "refresh_frequency": openapi.Schema(type=openapi.TYPE_STRING)}),
                         responses={'200': openapi.Response("Refresh Schedule updated", RequestRefreshScheduleSerializer()),
                                    '400': openapi.Response("Bad Request")})
    def partial_update(self, request, *args, **kwargs):
        response = super().partial_update(request, *args, **kwargs)
        requests_refresher_service.reset_schedule_crontab(refresh_schedule=self.get_object())
        return response
