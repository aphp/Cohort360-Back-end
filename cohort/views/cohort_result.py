import logging

from django.db.models import Q, F
from django.http import HttpResponse, JsonResponse, Http404, QueryDict
from django_filters import rest_framework as filters, OrderingFilter
from django.utils import timezone
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response
from rest_framework_extensions.mixins import NestedViewSetMixin

from accesses.models import get_user_valid_manual_accesses_queryset
from admin_cohort.settings import SJS_USERNAME, ETL_USERNAME
from admin_cohort.tools import join_qs
from admin_cohort.types import JobStatus
from admin_cohort.views import SwaggerSimpleNestedViewSetMixin
from cohort.conf_cohort_job_api import fhir_to_job_status
from cohort.models import CohortResult
from cohort.permissions import SJSandETLCallbackPermission
from cohort.serializers import CohortResultSerializer, CohortResultSerializerFullDatedMeasure, CohortRightsSerializer
from cohort.tools import get_dict_cohort_pop_source, get_all_cohorts_rights, send_email_notif_about_large_cohort
from cohort.views.shared import UserObjectsRestrictedViewSet


_logger = logging.getLogger('info')


class CohortFilter(filters.FilterSet):
    name = filters.CharFilter(field_name='name', lookup_expr="icontains")
    min_result_size = filters.NumberFilter(field_name='dated_measure__measure', lookup_expr='gte')
    max_result_size = filters.NumberFilter(field_name='dated_measure__measure', lookup_expr='lte')
    # ?min_created_at=2015-04-23
    min_fhir_datetime = filters.IsoDateTimeFilter(field_name='dated_measure__fhir_datetime', lookup_expr="gte")
    max_fhir_datetime = filters.IsoDateTimeFilter(field_name='dated_measure__fhir_datetime', lookup_expr="lte")
    request_id = filters.CharFilter(field_name='request_query_snapshot__request__pk')

    # unused, untested
    def perimeter_filter(self, queryset, field, value):
        return queryset.filter(request_query_snapshot__perimeters_ids__contains=[value])

    def perimeters_filter(self, queryset, field, value):
        return queryset.filter(request_query_snapshot__perimeters_ids__contains=value.split(","))

    def multi_value_filter(self, queryset, field, value: str):
        if value:
            sub_values = [val.strip() for val in value.split(",")]
            return queryset.filter(join_qs([Q(**{field: v}) for v in sub_values]))
        return queryset

    type = filters.AllValuesMultipleFilter()
    perimeter_id = filters.CharFilter(method="perimeter_filter")
    perimeters_ids = filters.CharFilter(method="perimeters_filter")
    fhir_group_id = filters.CharFilter(method="multi_value_filter", field_name="fhir_group_id")
    status = filters.CharFilter(method="multi_value_filter", field_name="request_job_status")

    ordering = OrderingFilter(fields=('-created_at',
                                      'modified_at',
                                      'name',
                                      ('dated_measure__measure', 'result_size'),
                                      ('dated_measure__fhir_datetime', 'fhir_datetime'),
                                      'type',
                                      'favorite',
                                      'request_job_status'))

    class Meta:
        model = CohortResult
        fields = ('name',
                  'min_result_size',
                  'max_result_size',
                  'min_fhir_datetime',
                  'max_fhir_datetime',
                  'favorite',
                  'fhir_group_id',
                  'create_task_id',
                  'request_query_snapshot',
                  'request_query_snapshot__request',
                  'request_id',
                  'request_job_status',
                  'status',
                  # unused, untested
                  'type',
                  'perimeter_id',
                  'perimeters_ids')


class CohortResultViewSet(NestedViewSetMixin, UserObjectsRestrictedViewSet):
    queryset = CohortResult.objects.select_related('request_query_snapshot__request') \
                                   .annotate(request_id=F('request_query_snapshot__request__uuid')).all()
    serializer_class = CohortResultSerializer
    http_method_names = ['get', 'post', 'patch', 'delete']
    lookup_field = "uuid"
    swagger_tags = ['Cohort - cohorts']
    pagination_class = LimitOffsetPagination
    filterset_class = CohortFilter
    search_fields = ('$name', '$description')

    def get_permissions(self):
        sjs_etl_users = [SJS_USERNAME, ETL_USERNAME]
        if self.request.method == "PATCH" and self.request.user.provider_username in sjs_etl_users:
            return [SJSandETLCallbackPermission()]
        return super(CohortResultViewSet, self).get_permissions()

    def get_queryset(self):
        sjs_etl_users = [SJS_USERNAME, ETL_USERNAME]
        if self.request.method == "PATCH" and self.request.user.provider_username in sjs_etl_users:
            return self.queryset
        return super(CohortResultViewSet, self).get_queryset()

    def get_serializer_class(self):
        if self.request.method in ["POST", "PUT", "PATCH"] \
                and "dated_measure" in self.request.data \
                and isinstance(self.request.data["dated_measure"], dict) \
                or self.request.method == "GET":
            return CohortResultSerializerFullDatedMeasure
        return self.serializer_class

    @action(methods=['get'], detail=False, url_path='jobs/active')
    def get_active_jobs(self, request, *args, **kwargs):
        active_statuses = [JobStatus.new, JobStatus.validated, JobStatus.started, JobStatus.pending]
        jobs_count = CohortResult.objects.filter(request_job_status__in=active_statuses).count()
        if not jobs_count:
            return HttpResponse(status=status.HTTP_204_NO_CONTENT)
        return JsonResponse(data={"jobs_count": jobs_count}, status=status.HTTP_200_OK)

    @swagger_auto_schema(method='get',
                         operation_summary="Give cohorts aggregation read patient rights, export csv rights and "
                                           "transfer jupyter rights. It check accesses with perimeters population "
                                           "source for each cohort found.",
                         responses={'201': openapi.Response("Cohorts rights found", CohortRightsSerializer())})
    @action(detail=False, methods=['get'], url_path="cohort-rights")
    def get_cohort_right_accesses(self, request, *args, **kwargs):
        user_accesses = get_user_valid_manual_accesses_queryset(self.request.user)

        if not user_accesses:
            raise Http404("ERROR: No Accesses found")
        if self.request.query_params:
            # Case with perimeters search params
            cohorts_filtered_by_search = self.filter_queryset(self.get_queryset())
            if not cohorts_filtered_by_search:
                raise Http404("ERROR: No Cohort Found")
            list_cohort_id = [cohort.fhir_group_id for cohort in cohorts_filtered_by_search if cohort.fhir_group_id]
            cohort_dict_pop_source = get_dict_cohort_pop_source(list_cohort_id)

            return Response(CohortRightsSerializer(get_all_cohorts_rights(user_accesses, cohort_dict_pop_source),
                                                   many=True).data)

        all_user_cohorts = CohortResult.objects.filter(owner=self.request.user)
        if not all_user_cohorts:
            return Response("WARN: You do not have any cohort")
        list_cohort_id = [cohort.fhir_group_id for cohort in all_user_cohorts if cohort.fhir_group_id]
        cohort_dict_pop_source = get_dict_cohort_pop_source(list_cohort_id)
        return Response(CohortRightsSerializer(get_all_cohorts_rights(user_accesses, cohort_dict_pop_source),
                                               many=True).data)

    @swagger_auto_schema(operation_summary="Used by Front to update cohort's name, description and favorite."
                                           "By SJS to update cohort's request_job_status, request_job_duration and "
                                           "fhir_group_id. Also update count on DM."
                                           "By ETL to update request_job_status on delayed large cohorts",
                         request_body=openapi.Schema(
                             type=openapi.TYPE_OBJECT,
                             properties={"job_status": openapi.Schema(type=openapi.TYPE_STRING,
                                                                      description="For SJS callback"),
                                         "group.id": openapi.Schema(type=openapi.TYPE_STRING,
                                                                    description="For SJS callback"),
                                         "group.count": openapi.Schema(type=openapi.TYPE_STRING,
                                                                       description="For SJS callback"),
                                         "request_job_status": openapi.Schema(type=openapi.TYPE_STRING,
                                                                              description="For ETL callback")},
                             required=['job_status', 'group.id', 'group.count', 'request_job_status']),
                         responses={'200': openapi.Response("Cohort updated successfully", CohortRightsSerializer()),
                                    '400': openapi.Response("Bad Request")})
    def partial_update(self, request, *args, **kwargs):
        data = request.data
        cohort = self.get_object()
        sjs_data_keys = ("job_status", "group.id", "group.count")
        update_from_sjs = all([key in data for key in sjs_data_keys])
        update_from_etl = "request_job_status" in data

        if "job_status" in data:
            job_status = fhir_to_job_status().get(data.pop("job_status"))
            if not job_status:
                return Response(data=f"Invalid job status: {data.get('status')}",
                                status=status.HTTP_400_BAD_REQUEST)
            data["request_job_status"] = job_status
            if job_status in (JobStatus.finished, JobStatus.failed):
                data["request_job_duration"] = str(timezone.now() - cohort.created_at)
                if job_status == JobStatus.failed:
                    data["request_job_fail_msg"] = "Received a failed status from SJS"
        if "group.id" in data:
            data["fhir_group_id"] = data.pop("group.id")
        if "group.count" in data:
            cohort.dated_measure.measure = data.pop("group.count")
            cohort.dated_measure.save()

        resp = super(CohortResultViewSet, self).partial_update(request, *args, **kwargs)

        if status.is_success(resp.status_code):
            if update_from_sjs:
                _logger.info("CohortResult successfully updated from SJS")
            if update_from_etl:
                send_email_notif_about_large_cohort(cohort.name, cohort.fhir_group_id, cohort.owner)
        return resp


class NestedCohortResultViewSet(SwaggerSimpleNestedViewSetMixin, CohortResultViewSet):
    def create(self, request, *args, **kwargs):
        if type(request.data) == QueryDict:
            request.data._mutable = True
        if 'request_query_snapshot' in kwargs:
            request.data["request_query_snapshot"] = kwargs['request_query_snapshot']
        return super(NestedCohortResultViewSet, self).create(request, *args, **kwargs)
