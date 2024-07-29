import logging

from django.db import transaction
from django_filters import rest_framework as filters, OrderingFilter
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework_extensions.mixins import NestedViewSetMixin

from admin_cohort.tools.cache import cache_response
from admin_cohort.tools.negative_limit_paginator import NegativeLimitOffsetPagination
from cohort.models import DatedMeasure
from cohort.serializers import DatedMeasureSerializer, DatedMeasureCreateSerializer, DatedMeasurePatchSerializer
from cohort.services.dated_measure import dm_service
from cohort.services.utils import await_celery_task
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
    swagger_tags = ['Dated Measures']
    filterset_class = DatedMeasureFilter
    pagination_class = NegativeLimitOffsetPagination

    def get_permissions(self):
        special_permissions = dm_service.get_special_permissions(self.request)
        if special_permissions:
            return special_permissions
        return super().get_permissions()

    def get_queryset(self):
        if dm_service.allow_use_full_queryset(request=self.request):
            return self.queryset
        return super().get_queryset()

    @extend_schema(tags=swagger_tags,
                   responses={status.HTTP_200_OK: DatedMeasureSerializer})
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(tags=swagger_tags,
                   responses={status.HTTP_200_OK: DatedMeasureSerializer})
    @cache_response()
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(tags=swagger_tags,
                   request=DatedMeasureCreateSerializer,
                   responses={status.HTTP_201_CREATED: DatedMeasureSerializer})
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        transaction.on_commit(lambda: dm_service.handle_count(request=request,
                                                              dm=response.data.serializer.instance))
        return response

    @extend_schema(tags=swagger_tags,
                   request=DatedMeasurePatchSerializer,
                   responses={status.HTTP_200_OK: DatedMeasureSerializer})
    @await_celery_task
    def partial_update(self, request, *args, **kwargs):
        dm = self.get_object()
        try:
            dm_service.handle_patch_dated_measure(dm=dm, data=request.data)
        except ValueError as ve:
            dm_service.mark_dm_as_failed(dm=dm, reason=str(ve))
            response = Response(data=str(ve), status=status.HTTP_400_BAD_REQUEST)
        else:
            response = super().partial_update(request, *args, **kwargs)
        dm_service.ws_send_to_client(dm=dm)
        return response
