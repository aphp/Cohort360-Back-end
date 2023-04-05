import logging

from django.http import QueryDict
from django_filters import rest_framework as filters, OrderingFilter
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response
from rest_framework_extensions.mixins import NestedViewSetMixin

from cohort.conf_cohort_job_api import get_authorization_header, cancel_job
from cohort.models import DatedMeasure, RequestQuerySnapshot
from cohort.serializers import DatedMeasureSerializer
from cohort.views.shared import UserObjectsRestrictedViewSet

_logger = logging.getLogger('django.request')


class DMFilter(filters.FilterSet):
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
    http_method_names = ['get', 'post', 'patch', 'delete']
    lookup_field = "uuid"
    swagger_tags = ['Cohort - dated-measures']
    filterset_class = DMFilter
    pagination_class = LimitOffsetPagination

    def create(self, request, *args, **kwargs):
        if not ("request_query_snapshot_id" in request.data or "request_query_snapshot" in kwargs):
            _logger.exception("RequestQuerySnapshot UUID not provided")
            return Response(status=status.HTTP_400_BAD_REQUEST)
        return super(DatedMeasureViewSet, self).create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        return Response(data="Updating a DatedMeasure is not allowed",
                        status=status.HTTP_403_FORBIDDEN)

    def destroy(self, request, *args, **kwargs):
        dm = self.get_object()
        if dm.cohort.count():
            return Response(data={'message': "Cannot delete a DatedMeasure bound to a CohortResult"},
                            status=status.HTTP_403_FORBIDDEN)
        return super(DatedMeasureViewSet, self).destroy(request, *args, **kwargs)

    @action(methods=['patch'], detail=True, url_path='abort')
    def abort(self, request, *args, **kwargs):
        # todo: check this is not used
        dm = self.get_object()
        try:
            cancel_job(dm.request_job_id, get_authorization_header(request))
        except Exception as e:
            return Response(dict(message=str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
