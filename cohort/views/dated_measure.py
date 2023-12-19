import logging

from django.db import transaction
from django.http import FileResponse
from django_filters import rest_framework as filters, OrderingFilter
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_extensions.mixins import NestedViewSetMixin

from admin_cohort.tools.cache import cache_response
from admin_cohort.tools.negative_limit_paginator import NegativeLimitOffsetPagination
from cohort.models import DatedMeasure
from cohort.permissions import SJSorETLCallbackPermission
from cohort.serializers import DatedMeasureSerializer
from cohort.services.dated_measure import dated_measure_service, JOB_STATUS, MINIMUM, MAXIMUM, COUNT, EXTRA
from cohort.services.misc import is_sjs_user
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
    http_method_names = ['get', 'post', 'patch']
    lookup_field = "uuid"
    swagger_tags = ['Cohort - dated-measures']
    filterset_class = DatedMeasureFilter
    pagination_class = NegativeLimitOffsetPagination

    def get_permissions(self):
        if is_sjs_user(request=self.request):
            return [SJSorETLCallbackPermission()]
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
                             properties={"request_query_snapshot_id": openapi.Schema(type=openapi.TYPE_STRING)},
                             required=["request_query_snapshot_id"]),
                         manual_parameters=[openapi.Parameter(name="feasibility", in_=openapi.IN_QUERY, type=openapi.TYPE_BOOLEAN,
                                                              description="Launch a count request to get feasibility report")],
                         responses={'200': openapi.Response("DatedMeasure created", DatedMeasureSerializer()),
                                    '400': openapi.Response("Bad Request")})
    @transaction.atomic
    def create(self, request, *args, **kwargs):
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
                                         COUNT: openapi.Schema(type=openapi.TYPE_STRING, description="For SJS callback"),
                                         EXTRA: openapi.Schema(type=openapi.TYPE_STRING, description="For SJS callback, for feasibility reports")},
                             required=[JOB_STATUS, MINIMUM, MAXIMUM, COUNT]),
                         responses={'200': openapi.Response("DatedMeasure updated successfully", DatedMeasureSerializer()),
                                    '400': openapi.Response("Bad Request")})
    def partial_update(self, request, *args, **kwargs):
        try:
            dated_measure_service.process_patch_data(dm=self.get_object(), data=request.data)
        except ValueError as ve:
            return Response(data=f"{ve}", status=status.HTTP_400_BAD_REQUEST)
        return super(DatedMeasureViewSet, self).partial_update(request, *args, **kwargs)

    @action(detail=True, methods=['get'], url_path='feasibility')
    def download_feasibility_report(self, request, *args, **kwargs):
        dm = self.get_object()
        if not dm.feasibility_report:
            return Response(data="Missing report", status=status.HTTP_404_NOT_FOUND)
        file_name = f"rapport_etude_de_faisabilite_{dm.created_at.strftime('%d-%m-%Y')}.zip"
        response = FileResponse(dm.feasibility_report, content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="{file_name}"'
        return response

    # todo: add a periodic task to delete saved .zip files in DB

