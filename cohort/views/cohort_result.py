from django.db import transaction
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
from cohort.permissions import SJSorETLCallbackPermission
from cohort.serializers import CohortResultSerializer, CohortResultSerializerFullDatedMeasure
from cohort.services.cohort_rights import cohort_rights_service
from cohort.services.misc import is_sjs_or_etl_user
from cohort.services.ws_event_manager import ws_send_to_client
from cohort.views.shared import UserObjectsRestrictedViewSet
from exports.services.export import export_service


class CohortFilter(filters.FilterSet):
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

    name = filters.CharFilter(field_name='name', lookup_expr="icontains")
    min_result_size = filters.NumberFilter(field_name='dated_measure__measure', lookup_expr='gte')
    max_result_size = filters.NumberFilter(field_name='dated_measure__measure', lookup_expr='lte')
    # ?min_created_at=2015-04-23
    min_fhir_datetime = filters.IsoDateTimeFilter(field_name='dated_measure__fhir_datetime', lookup_expr="gte")
    max_fhir_datetime = filters.IsoDateTimeFilter(field_name='dated_measure__fhir_datetime', lookup_expr="lte")
    request_id = filters.CharFilter(field_name='request_query_snapshot__request__pk')
    type = filters.AllValuesMultipleFilter()
    perimeter_id = filters.CharFilter(method="perimeter_filter")
    perimeters_ids = filters.CharFilter(method="perimeters_filter")
    group_id = filters.CharFilter(method="multi_value_filter", field_name="group_id")
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
                  'group_id',
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
    non_updatable_fields = ['owner', 'owner_id',
                            'request_query_snapshot', 'request_query_snapshot_id',
                            'dated_measure', 'dated_measure_id']

    def get_permissions(self):
        if is_sjs_or_etl_user(request=self.request):
            return [SJSorETLCallbackPermission()]
        if self.action == 'get_active_jobs':
            return [AllowAny()]
        return super(CohortResultViewSet, self).get_permissions()

    def get_queryset(self):
        if is_sjs_or_etl_user(request=self.request):
            return self.queryset
        return super(CohortResultViewSet, self).get_queryset()\
                                               .filter(is_subset=False)

    def get_serializer_class(self):
        if self.request.method in ["POST", "PUT", "PATCH"] \
                and "dated_measure" in self.request.data \
                and isinstance(self.request.data["dated_measure"], dict) \
                or self.request.method == "GET":
            return CohortResultSerializerFullDatedMeasure
        return self.serializer_class

    @action(methods=['get'], detail=False, url_path='jobs/active')
    def get_active_jobs(self, request, *args, **kwargs):
        return Response(data={"jobs_count": cohort_service.count_active_jobs()},
                        status=status.HTTP_200_OK)

    @cache_response()
    def list(self, request, *args, **kwargs):
        return super(CohortResultViewSet, self).list(request, *args, **kwargs)

    @swagger_auto_schema(operation_summary="Create a CohortResult",
                         request_body=openapi.Schema(
                             type=openapi.TYPE_OBJECT,
                             properties={"dated_measure_id": openapi.Schema(type=openapi.TYPE_STRING),
                                         "request_query_snapshot_id": openapi.Schema(type=openapi.TYPE_STRING),
                                         "request_id": openapi.Schema(type=openapi.TYPE_STRING),
                                         "name": openapi.Schema(type=openapi.TYPE_STRING),
                                         "description": openapi.Schema(type=openapi.TYPE_STRING),
                                         "global_estimate": openapi.Schema(type=openapi.TYPE_BOOLEAN, default=True)}),
                         responses={'201': openapi.Response("CohortResult created successfully"),
                                    '400': openapi.Response("Bad Request")})
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        transaction.on_commit(lambda: cohort_service.proceed_with_cohort_creation(request=request,
                                                                                  cohort=response.data.serializer.instance))
        return response

    @swagger_auto_schema(operation_summary="Used by Front to update cohort's name, description and favorite."
                                           "By SJS to update cohort's request_job_status, request_job_duration and "
                                           "group_id. Also update count on DM."
                                           "By ETL to update request_job_status on delayed large cohorts",
                         request_body=openapi.Schema(
                             type=openapi.TYPE_OBJECT,
                             properties={JOB_STATUS: openapi.Schema(type=openapi.TYPE_STRING, description="For SJS and ETL callback"),
                                         GROUP_ID: openapi.Schema(type=openapi.TYPE_STRING, description="For SJS callback"),
                                         GROUP_COUNT: openapi.Schema(type=openapi.TYPE_STRING, description="For SJS callback"),
                                         "name": openapi.Schema(type=openapi.TYPE_STRING),
                                         "description": openapi.Schema(type=openapi.TYPE_STRING),
                                         "favorite": openapi.Schema(type=openapi.TYPE_STRING)},
                             required=[JOB_STATUS, GROUP_ID, GROUP_COUNT]),
                         responses={'200': openapi.Response("Cohort updated successfully"),
                                    '400': openapi.Response("Bad Request")})
    def partial_update(self, request, *args, **kwargs):
        for field in self.non_updatable_fields:
            if field in request.data:
                return Response(data=f"`{field}` field cannot be updated",
                                status=status.HTTP_400_BAD_REQUEST)
        cohort = self.get_object()
        try:
            is_update_from_sjs, is_update_from_etl = cohort_service.process_patch_data(cohort=cohort,
                                                                                       data=request.data)
        except ValueError as ve:
            return Response(data=f"{ve}", status=status.HTTP_400_BAD_REQUEST)
        response = super(CohortResultViewSet, self).partial_update(request, *args, **kwargs)
        cohort.refresh_from_db()
        global_dm = cohort.dated_measure_global
        extra_info = {'group_id': cohort.group_id}
        if global_dm:
            extra_info['global'] = {'measure_min': global_dm.measure_min,
                                    'measure_max': global_dm.measure_max
                                    }
        ws_send_to_client(_object=cohort, job_name='create', extra_info=extra_info)
        if status.is_success(response.status_code):
            if is_update_from_sjs and cohort.export_table.exists():
                export_service.check_all_cohort_subsets_created(export=cohort.export_table.first().export)
            cohort_service.send_email_notification(cohort=cohort,
                                                   is_update_from_sjs=is_update_from_sjs,
                                                   is_update_from_etl=is_update_from_etl)
        return response

    @swagger_auto_schema(method='get',
                         operation_summary="Returns a dict of rights (booleans) for each cohort based on user accesses."
                                           "Rights are computed by checking user accesses against every perimeter the cohort is built upon",
                         responses={'200': openapi.Response("Cohorts rights found"),
                                    '404': openapi.Response("No cohorts found matching the given group_ids or user has no valid accesses")})
    @action(detail=False, methods=['get'], url_path="cohort-rights")
    def get_rights_on_cohorts(self, request, *args, **kwargs):
        cohorts_rights = cohort_rights_service.get_user_rights_on_cohorts(group_ids=request.query_params.get('group_id'),
                                                                          user=request.user)
        return Response(data=cohorts_rights, status=status.HTTP_200_OK)
