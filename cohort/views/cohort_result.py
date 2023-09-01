from django.db.models import Q, F
from django_filters import rest_framework as filters, OrderingFilter
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_extensions.mixins import NestedViewSetMixin

from admin_cohort.tools.cache import cache_response
from admin_cohort.tools import join_qs
from admin_cohort.tools.negative_limit_paginator import NegativeLimitOffsetPagination
from cohort.services.cohort_result import cohort_service, JOB_STATUS, GROUP_ID, GROUP_COUNT
from cohort.models import CohortResult
from cohort.permissions import SJSandETLCallbackPermission
from cohort.serializers import CohortResultSerializer, CohortResultSerializerFullDatedMeasure, CohortRightsSerializer
from cohort.tools import is_sjs_or_etl_user
from cohort.views.shared import UserObjectsRestrictedViewSet


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
    pagination_class = NegativeLimitOffsetPagination
    filterset_class = CohortFilter
    search_fields = ('$name', '$description')

    def get_permissions(self):
        if is_sjs_or_etl_user(request=self.request):
            return [SJSandETLCallbackPermission()]
        if self.action == 'get_active_jobs':
            return [AllowAny()]
        return super(CohortResultViewSet, self).get_permissions()

    def get_queryset(self):
        if is_sjs_or_etl_user(request=self.request):
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
        jobs_count = cohort_service.count_active_jobs()
        return Response(data={"jobs_count": jobs_count}, status=status.HTTP_200_OK)

    @cache_response()
    def list(self, request, *args, **kwargs):
        return super(CohortResultViewSet, self).list(request, *args, **kwargs)

    @swagger_auto_schema(method='get',
                         operation_summary="Give cohorts aggregation read patient rights, export csv rights and "
                                           "transfer jupyter rights. It check accesses with perimeters population "
                                           "source for each cohort found.",
                         responses={'201': openapi.Response("Cohorts rights found", CohortRightsSerializer())})
    @action(detail=False, methods=['get'], url_path="cohort-rights")
    def get_cohort_right_accesses(self, request, *args, **kwargs):
        cohorts = self.filter_queryset(self.get_queryset())
        cohorts_rights = cohort_service.get_cohorts_rights(cohorts=cohorts, user=request.user)
        return Response(data=CohortRightsSerializer(data=cohorts_rights, many=True).data)

    @swagger_auto_schema(operation_summary="Used by Front to update cohort's name, description and favorite."
                                           "By SJS to update cohort's request_job_status, request_job_duration and "
                                           "fhir_group_id. Also update count on DM."
                                           "By ETL to update request_job_status on delayed large cohorts",
                         request_body=openapi.Schema(
                             type=openapi.TYPE_OBJECT,
                             properties={JOB_STATUS: openapi.Schema(type=openapi.TYPE_STRING, description="For SJS and ETL callback"),
                                         GROUP_ID: openapi.Schema(type=openapi.TYPE_STRING, description="For SJS callback"),
                                         GROUP_COUNT: openapi.Schema(type=openapi.TYPE_STRING, description="For SJS callback")},
                             required=[JOB_STATUS, GROUP_ID, GROUP_COUNT]),
                         responses={'200': openapi.Response("Cohort updated successfully", CohortRightsSerializer()),
                                    '400': openapi.Response("Bad Request")})
    def partial_update(self, request, *args, **kwargs):
        cohort = self.get_object()
        is_update_from_sjs, is_update_from_etl = cohort_service.process_patch_data(cohort=cohort,
                                                                                   data=request.data)
        response = super(CohortResultViewSet, self).partial_update(request, *args, **kwargs)
        if status.is_success(response.status_code):
            cohort_service.send_email_notification(cohort=cohort,
                                                   is_update_from_sjs=is_update_from_sjs,
                                                   is_update_from_etl=is_update_from_etl)
        return response
