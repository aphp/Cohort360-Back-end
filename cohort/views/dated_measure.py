import logging

from django.http import HttpResponseBadRequest, HttpResponseServerError, QueryDict
from django_filters import rest_framework as filters, OrderingFilter
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response
from rest_framework_extensions.mixins import NestedViewSetMixin

from admin_cohort import app
from admin_cohort.types import JobStatus
from admin_cohort.views import SwaggerSimpleNestedViewSetMixin
from cohort.conf_cohort_job_api import get_authorization_header, cancel_job
from cohort.models import DatedMeasure, CohortResult, RequestQuerySnapshot
from cohort.serializers import DatedMeasureSerializer
from cohort.views import UserObjectsRestrictedViewSet

_log = logging.getLogger('django.request')


class DMFilter(filters.FilterSet):
    request_id = filters.CharFilter(field_name='request_query_snapshot__request__pk')
    ordering = OrderingFilter(fields=("-created_at", "modified_at", "result_size"))

    class Meta:
        model = DatedMeasure
        fields = ('uuid',
                  'request_query_snapshot',
                  'mode',
                  'count_task_id',
                  'request_query_snapshot__request',
                  'request_id'
                  )


class DatedMeasureViewSet(NestedViewSetMixin, UserObjectsRestrictedViewSet):
    queryset = DatedMeasure.objects.all()
    serializer_class = DatedMeasureSerializer
    http_method_names = ['get', 'post', 'patch', 'delete']
    lookup_field = "uuid"
    swagger_tags = ['Cohort - dated-measures']

    filterset_class = DMFilter
    pagination_class = LimitOffsetPagination

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if CohortResult.objects.filter(dated_measure__uuid=instance.uuid).first():
            return Response({'message': "Cannot delete a DatedMeasure bound to a CohortResult"},
                            status=status.HTTP_403_FORBIDDEN)
        return super(DatedMeasureViewSet, self).destroy(request, *args, **kwargs)

    @action(methods=['post'], detail=False, url_path='create-unique')
    def create_unique(self, request, *args, **kwargs):
        """ Demande à l'API FHIR d'annuler tous les jobs de calcul de count liés à
            une construction de Requête avant d'en créer un nouveau
        """
        if "request_query_snapshot" in kwargs:
            rqs_id = kwargs['request_query_snapshot']
        elif "request_query_snapshot_id" in request.data:
            rqs_id = request.data.get("request_query_snapshot_id")
        else:
            _log.exception("'request_query_snapshot_id' not provided")
            return HttpResponseBadRequest()

        try:
            rqs: RequestQuerySnapshot = RequestQuerySnapshot.objects.get(pk=rqs_id)
        except RequestQuerySnapshot.DoesNotExist:
            _log.exception("Invalid 'request_query_snapshot_id'")
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
                msg = f"Error while cancelling {status} job [{job.request_job_id}] DM [{job.uuid}] - {e}"
                _log.exception(msg)
                job.request_job_status = JobStatus.failed
                job.request_job_fail_msg = msg
                job.save()
                return HttpResponseServerError()
        return self.create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        return Response("Updating a dated measure is not allowed",
                        status=status.HTTP_403_FORBIDDEN)

    @action(methods=['patch'], detail=True, url_path='abort')
    def abort(self, request, *args, **kwargs):
        """
        Demande à l'API FHIR d'annuler le job de calcul de count d'une requête
        """
        # TODO : test
        instance: DatedMeasure = self.get_object()
        try:
            cancel_job(instance.request_job_id, get_authorization_header(request))
        except Exception as e:
            return Response(dict(message=str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class NestedDatedMeasureViewSet(SwaggerSimpleNestedViewSetMixin,
                                DatedMeasureViewSet):
    @swagger_auto_schema(auto_schema=None)
    def abort(self, request, *args, **kwargs):
        return self.abort(self, request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        if type(request.data) == QueryDict:
            request.data._mutable = True

        if 'request_query_snapshot' in kwargs:
            request.data["request_query_snapshot"] \
                = kwargs['request_query_snapshot']

        return super(NestedDatedMeasureViewSet, self).create(
            request, *args, **kwargs)
