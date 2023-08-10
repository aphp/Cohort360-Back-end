import logging

from django.utils import timezone
from django_filters import rest_framework as filters, OrderingFilter
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response
from rest_framework_extensions.mixins import NestedViewSetMixin

from admin_cohort.tools.cache import cache_response
from admin_cohort.types import JobStatus
from cohort.conf_cohort_job_api import fhir_to_job_status
from cohort.models import DatedMeasure
from cohort.models.dated_measure import GLOBAL_DM_MODE
from cohort.permissions import SJSandETLCallbackPermission
from cohort.serializers import DatedMeasureSerializer
from cohort.tools import is_sjs_user
from cohort.views.shared import UserObjectsRestrictedViewSet

JOB_STATUS = "request_job_status"
COUNT = "count"
MAXIMUM = "maximum"
MINIMUM = "minimum"
ERR_MESSAGE = "message"

_logger = logging.getLogger('info')
_logger_err = logging.getLogger('django.request')


class DatedMeasureFilter(filters.FilterSet):
    request_id = filters.CharFilter(field_name='request_query_snapshot__request__pk')
    ordering = OrderingFilter(fields=("-created_at", "modified_at", "result_size"))

    class Meta:
        model = DatedMeasure
        fields = ('uuid',
                  'mode',
                  'request_id',
                  'count_task_id',
                  'request_query_snapshot',
                  'request_query_snapshot__request')


class DatedMeasureViewSet(NestedViewSetMixin, UserObjectsRestrictedViewSet):
    queryset = DatedMeasure.objects.all()
    serializer_class = DatedMeasureSerializer
    http_method_names = ['get', 'post', 'patch']
    lookup_field = "uuid"
    swagger_tags = ['Cohort - dated-measures']
    filterset_class = DatedMeasureFilter
    pagination_class = LimitOffsetPagination

    def get_permissions(self):
        if is_sjs_user(request=self.request):
            return [SJSandETLCallbackPermission()]
        return super(DatedMeasureViewSet, self).get_permissions()

    def get_queryset(self):
        if is_sjs_user(request=self.request):
            return self.queryset
        return super(DatedMeasureViewSet, self).get_queryset()

    @cache_response()
    def list(self, request, *args, **kwargs):
        return super(DatedMeasureViewSet, self).list(request, *args, **kwargs)

    @swagger_auto_schema(operation_summary="Called by SJS to update DM's `measure` and other fields",
                         request_body=openapi.Schema(
                             type=openapi.TYPE_OBJECT,
                             properties={JOB_STATUS: openapi.Schema(type=openapi.TYPE_STRING, description="For SJS callback"),
                                         MINIMUM: openapi.Schema(type=openapi.TYPE_STRING, description="For SJS callback"),
                                         MAXIMUM: openapi.Schema(type=openapi.TYPE_STRING, description="For SJS callback"),
                                         COUNT: openapi.Schema(type=openapi.TYPE_STRING, description="For SJS callback")},
                             required=[JOB_STATUS, MINIMUM, MAXIMUM, COUNT]),
                         responses={'200': openapi.Response("DatedMeasure updated successfully", DatedMeasureSerializer()),
                                    '400': openapi.Response("Bad Request")})
    def partial_update(self, request, *args, **kwargs):
        data: dict = request.data
        _logger.info(f"Received data for DM patch: {data}")

        job_status = data.get(JOB_STATUS, "")
        job_status = fhir_to_job_status().get(job_status.upper())
        if not job_status:
            return Response(data=f"Invalid job status: {data.get(JOB_STATUS)}",
                            status=status.HTTP_400_BAD_REQUEST)
        dm = self.get_object()
        job_duration = str(timezone.now() - dm.created_at)

        if job_status == JobStatus.finished:
            if dm.mode == GLOBAL_DM_MODE:
                data.update({"measure_min": data.pop(MINIMUM, None),
                             "measure_max": data.pop(MAXIMUM, None)
                             })
            else:
                data["measure"] = data.pop(COUNT, None)
            _logger.info(f"DatedMeasure [{dm.uuid}] successfully updated from SJS")
        else:
            data["request_job_fail_msg"] = data.pop(ERR_MESSAGE, None)
            _logger_err.exception(f"DatedMeasure [{dm.uuid}] - Error on SJS callback")

        data.update({"request_job_status": job_status,
                     "request_job_duration": job_duration
                     })
        return super(DatedMeasureViewSet, self).partial_update(request, *args, **kwargs)

