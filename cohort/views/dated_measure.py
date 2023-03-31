import logging

from django.http import HttpResponseBadRequest, HttpResponseServerError, QueryDict
from django_filters import rest_framework as filters, OrderingFilter
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response
from rest_framework_extensions.mixins import NestedViewSetMixin

from admin_cohort import app
from admin_cohort.cache_utils import cache_response, invalidate_cache
from admin_cohort.types import JobStatus
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

    @action(methods=['post'], detail=False, url_path='create-unique')
    def create_unique(self, request, *args, **kwargs):
        if "request_query_snapshot" in kwargs:
            rqs_id = kwargs['request_query_snapshot']
        elif "request_query_snapshot_id" in request.data:
            rqs_id = request.data.get("request_query_snapshot_id")
        else:
            _logger.exception("'request_query_snapshot_id' not provided")
            return HttpResponseBadRequest()

        try:
            rqs: RequestQuerySnapshot = RequestQuerySnapshot.objects.get(pk=rqs_id)
        except RequestQuerySnapshot.DoesNotExist:
            _logger.exception("Invalid 'request_query_snapshot_id'")
            return HttpResponseBadRequest()

        dms_jobs = rqs.request.dated_measures.filter(request_job_status__in=[JobStatus.started, JobStatus.pending]) \
            .prefetch_related('cohort', 'restricted_cohort')
        for job in dms_jobs:
            if job.cohort.all() or job.restricted_cohort.all():
                continue  # if the dated measure is bound to a cohort, don't cancel it
            job_status = job.request_job_status
            try:
                if job_status == JobStatus.started:
                    headers = get_authorization_header(request)
                    new_status = cancel_job(job.request_job_id, headers)
                else:
                    app.control.revoke(job.count_task_id)
                job.request_job_status = job_status == JobStatus.started and new_status or JobStatus.cancelled
                job.save()
            except Exception as e:
                msg = f"Error while cancelling {job_status} job [{job.request_job_id}] DM [{job.uuid}] - {e}"
                _logger.exception(msg)
                job.request_job_status = JobStatus.failed
                job.request_job_fail_msg = msg
                job.save()
                return HttpResponseServerError()
        return self.create(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        return super(DatedMeasureViewSet, self).retrieve(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        return Response(data="Updating a DatedMeasure is not allowed",
                        status=status.HTTP_403_FORBIDDEN)

    def destroy(self, request, *args, **kwargs):
        dm = self.get_object()
        if dm.cohort.count():
            return Response(data={'message': "Cannot delete a DatedMeasure bound to a CohortResult"},
                            status=status.HTTP_403_FORBIDDEN)
        response = super(DatedMeasureViewSet, self).destroy(request, *args, **kwargs)
        invalidate_cache(view_instance=self, user=request.user)
        return response

    @action(methods=['patch'], detail=True, url_path='abort')
    def abort(self, request, *args, **kwargs):
        # todo: check this is not used
        dm = self.get_object()
        try:
            cancel_job(dm.request_job_id, get_authorization_header(request))
        except Exception as e:
            return Response(dict(message=str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class NestedDatedMeasureViewSet(DatedMeasureViewSet):

    def create(self, request, *args, **kwargs):
        if type(request.data) == QueryDict:
            request.data._mutable = True
        if 'request_query_snapshot' in kwargs:
            request.data["request_query_snapshot"] = kwargs['request_query_snapshot']
        return super(NestedDatedMeasureViewSet, self).create(request, *args, **kwargs)
