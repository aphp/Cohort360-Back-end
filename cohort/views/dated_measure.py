import logging

from django.utils import timezone
from django_filters import rest_framework as filters, OrderingFilter
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response
from rest_framework_extensions.mixins import NestedViewSetMixin

from admin_cohort.tools.cache import cache_response
from admin_cohort.types import JobStatus
from cohort.conf_cohort_job_api import fhir_to_job_status
from cohort.models import DatedMeasure
from cohort.serializers import DatedMeasureSerializer
from cohort.views.shared import UserObjectsRestrictedViewSet

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
    http_method_names = ['get', 'post']
    lookup_field = "uuid"
    swagger_tags = ['Cohort - dated-measures']
    filterset_class = DatedMeasureFilter
    pagination_class = LimitOffsetPagination

    @cache_response()
    def list(self, request, *args, **kwargs):
        return super(DatedMeasureViewSet, self).list(request, *args, **kwargs)

    @swagger_auto_schema(operation_summary="Called by SJS to update DM's `measure` and other fields",
                         request_body=openapi.Schema(
                             type=openapi.TYPE_OBJECT,
                             properties={"request_job_status": openapi.Schema(type=openapi.TYPE_STRING, description="For SJS and ETL callback"),
                                         "group.id": openapi.Schema(type=openapi.TYPE_STRING, description="For SJS callback"),
                                         "group.count": openapi.Schema(type=openapi.TYPE_STRING, description="For SJS callback")},
                             required=['request_job_status', 'group.id', 'group.count']),
                         responses={'200': openapi.Response("DatedMeasure updated successfully", DatedMeasureSerializer()),
                                    '400': openapi.Response("Bad Request")})
    def partial_update(self, request, *args, **kwargs):
        dm = self.get_object()
        data: dict = request.data

        status = data.get("fhir_job_status")
        job_status = fhir_to_job_status().get(data["request_job_status"].upper())
        if not job_status:
            return Response(data=f"Invalid job status: {data.get('status')}",
                            status=status.HTTP_400_BAD_REQUEST)
        job_duration = str(timezone.now() - dm.created_at)

        if status == JobStatus.finished:
            if dm.global_estimate:
                data.update({"measure_min": data.pop("count_min", None),
                             "measure_max": data.pop("count_max", None)
                             })
            else:
                data["measure"] = data.pop("count", None)
            _logger.info(f"DatedMeasure [{dm.uuid}] successfully updated from SJS")
        else:
            data["request_job_fail_msg"] = data.pop("err_msg", None)
            _logger_err.exception(f"DatedMeasure [{dm.uuid}] - Error on SJS callback")

        data.update({"request_job_status": status,
                     "request_job_duration": job_duration,
                     })
        return super(DatedMeasureViewSet, self).partial_update(request, *args, **kwargs)

