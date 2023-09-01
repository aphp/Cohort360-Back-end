import logging

from django.db import transaction
from django_filters import rest_framework as filters, OrderingFilter
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework_extensions.mixins import NestedViewSetMixin

from admin_cohort.tools.cache import cache_response
from admin_cohort.tools.negative_limit_paginator import NegativeLimitOffsetPagination
from cohort.models import DatedMeasure
from cohort.permissions import SJSandETLCallbackPermission
from cohort.serializers import DatedMeasureSerializer
from cohort.services.dated_measure import dated_measure_service
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
    pagination_class = NegativeLimitOffsetPagination

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

    @swagger_auto_schema(request_body=openapi.Schema(
                             type=openapi.TYPE_OBJECT,
                             properties={"request_query_snapshot_id": openapi.Schema(type=openapi.TYPE_STRING),
                                         "request_id": openapi.Schema(type=openapi.TYPE_STRING)},
                             required=["request_query_snapshot_id", "request_id"]),
                         responses={'200': openapi.Response("DatedMeasure created", DatedMeasureSerializer()),
                                    '400': openapi.Response("Bad Request")})
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        if not request.data.get("request_query_snapshot"):  # todo: check vis-à-vis required=True set on the serializer
            return Response(data="Invalid 'request_query_snapshot_id'",
                            status=status.HTTP_400_BAD_REQUEST)
        response = super().create(request, *args, **kwargs)
        transaction.on_commit(lambda: dated_measure_service.process_dated_measure(dm_uuid=response.data.get("uuid"),
                                                                                  request=request))
        return response

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
        dated_measure_service.process_patch_data(dm=self.get_object(),
                                                 data=request.data)
        return super(DatedMeasureViewSet, self).partial_update(request, *args, **kwargs)

