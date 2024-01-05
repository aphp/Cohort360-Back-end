import logging

from django.db import transaction
from django.http import FileResponse
from django_filters import rest_framework as filters, OrderingFilter
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from admin_cohort.tools.cache import cache_response
from admin_cohort.tools.negative_limit_paginator import NegativeLimitOffsetPagination
from cohort.models import FeasibilityStudy
from cohort.permissions import SJSorETLCallbackPermission
from cohort.serializers import FeasibilityStudySerializer
from cohort.services.feasibility_study import feasibility_study_service, JOB_STATUS, COUNT, EXTRA
from cohort.services.misc import is_sjs_user
from cohort.views.shared import UserObjectsRestrictedViewSet

_logger = logging.getLogger('info')
_logger_err = logging.getLogger('django.request')


class FeasibilityStudyFilter(filters.FilterSet):
    ordering = OrderingFilter(fields=("-created_at",))

    class Meta:
        model = FeasibilityStudy
        fields = ["created_at"]


class FeasibilityStudyViewSet(UserObjectsRestrictedViewSet):
    queryset = FeasibilityStudy.objects.all()
    serializer_class = FeasibilityStudySerializer
    http_method_names = ['get', 'post', 'patch']
    lookup_field = "uuid"
    swagger_tags = ['Cohort - feasibility-studies']
    filterset_class = FeasibilityStudyFilter
    pagination_class = NegativeLimitOffsetPagination

    def get_permissions(self):
        if is_sjs_user(request=self.request):
            return [SJSorETLCallbackPermission()]
        return super(FeasibilityStudyViewSet, self).get_permissions()

    def get_queryset(self):
        if is_sjs_user(request=self.request):
            return self.queryset
        return super(FeasibilityStudyViewSet, self).get_queryset()

    @cache_response()
    def list(self, request, *args, **kwargs):
        return super(FeasibilityStudyViewSet, self).list(request, *args, **kwargs)

    @swagger_auto_schema(request_body=openapi.Schema(
                             type=openapi.TYPE_OBJECT,
                             properties={"request_query_snapshot_id": openapi.Schema(type=openapi.TYPE_STRING)},
                             required=["request_query_snapshot_id"]),
                         responses={'200': openapi.Response("FeasibilityStudy created", FeasibilityStudySerializer()),
                                    '400': openapi.Response("Bad Request")})
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        transaction.on_commit(lambda: feasibility_study_service.process_feasibility_study_request(fs_uuid=response.data.get("uuid"),
                                                                                                  request=request))
        return response

    @swagger_auto_schema(operation_summary="Called by SJS with detailed counts",
                         request_body=openapi.Schema(
                             type=openapi.TYPE_OBJECT,
                             properties={JOB_STATUS: openapi.Schema(type=openapi.TYPE_STRING, description="SJS job status"),
                                         COUNT: openapi.Schema(type=openapi.TYPE_STRING, description="Total patient count"),
                                         EXTRA: openapi.Schema(type=openapi.TYPE_STRING, description="Detailed patient counts")},
                             required=[JOB_STATUS, COUNT, EXTRA]),
                         responses={'200': openapi.Response("FeasibilityStudy updated successfully", FeasibilityStudySerializer()),
                                    '400': openapi.Response("Bad Request")})
    def partial_update(self, request, *args, **kwargs):
        try:
            feasibility_study_service.process_patch_data(fs=self.get_object(), data=request.data)
        except ValueError as ve:
            return Response(data=f"{ve}", status=status.HTTP_400_BAD_REQUEST)
        return super(FeasibilityStudyViewSet, self).partial_update(request, *args, **kwargs)

    @action(detail=True, methods=['get'], url_path='download')
    def download_report(self, request, *args, **kwargs):
        fs = self.get_object()
        if not fs.report_file:
            return Response(data="Feasibility report not found", status=status.HTTP_404_NOT_FOUND)
        file_name = feasibility_study_service.get_file_name(fs=fs)
        response = FileResponse(fs.report_file, content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="{file_name}.zip"'
        return response
