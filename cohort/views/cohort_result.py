from django.db.models import Q, F
from django.http import QueryDict, HttpResponse, JsonResponse
from django_filters import rest_framework as filters, OrderingFilter
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response
from rest_framework_extensions.mixins import NestedViewSetMixin

from accesses.models import get_user_valid_manual_accesses_queryset
from admin_cohort.tools import join_qs
from admin_cohort.types import JobStatus
from admin_cohort.views import SwaggerSimpleNestedViewSetMixin
from cohort.models import CohortResult
from cohort.serializers import CohortResultSerializer, CohortResultSerializerFullDatedMeasure, CohortRightsSerializer
from cohort.tools import get_dict_cohort_pop_source, get_all_cohorts_rights
from cohort.views.utils import UserObjectsRestrictedViewSet


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

    def get_serializer_class(self):
        if self.request.method in ["POST", "PUT", "PATCH"] and "dated_measure" in self.request.data \
                and isinstance(self.request.data["dated_measure"], dict):
            return CohortResultSerializerFullDatedMeasure
        if self.request.method == "GET":
            return CohortResultSerializerFullDatedMeasure
        return super(CohortResultViewSet, self).get_serializer_class()

    def create(self, request, *args, **kwargs):
        if type(request.data) == QueryDict:
            request.data._mutable = True
        # todo remove possibility to post _id when Front is ready
        if 'dated_measure_id' not in request.data:
            if 'dated_measure' in request.data:
                dated_measure = request.data['dated_measure']
                if isinstance(dated_measure, dict):
                    if "request_query_snapshot" in request.data:
                        dated_measure["request_query_snapshot"] = request.data["request_query_snapshot"]
        else:
            request.data['dated_measure'] = request.data['dated_measure_id']

        return super(CohortResultViewSet, self).create(request, *args, **kwargs)

    @action(methods=['get'], detail=False, url_path='jobs/active')
    def get_active_jobs(self, request, *args, **kwargs):
        active_statuses = [JobStatus.new, JobStatus.validated, JobStatus.started, JobStatus.pending]
        jobs_count = CohortResult.objects.filter(request_job_status__in=active_statuses).count()
        if not jobs_count:
            return HttpResponse(status=status.HTTP_204_NO_CONTENT)
        return JsonResponse(data={"jobs_count": jobs_count}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        method='get',
        operation_summary="Give cohorts aggregation read patient rights, export csv rights and transfer jupyter rights."
                          "It check accesses with perimeters population source for each cohort found.",
        responses={'200': openapi.Response("give rights in caresite perimeters found", CohortRightsSerializer())})
    @action(detail=False, methods=['get'], url_path="cohort-rights")
    def get_cohorts_read_right_accesses(self, request, *args, **kwargs):
        user_accesses = get_user_valid_manual_accesses_queryset(self.request.user)

        if not user_accesses:
            return Response(data="No Accesses Found", status=status.HTTP_404_NOT_FOUND)
        if self.request.query_params:
            # Case with perimeters search params
            cohorts_filtered_by_search = self.filter_queryset(self.get_queryset())
            if not cohorts_filtered_by_search:
                return Response("No Cohort Found", status=status.HTTP_404_NOT_FOUND)
            list_cohort_id = [cohort.fhir_group_id for cohort in cohorts_filtered_by_search if cohort.fhir_group_id]
        else:
            all_user_cohorts = CohortResult.objects.filter(owner=self.request.user)
            if not all_user_cohorts:
                return Response("No Cohort Found", status=status.HTTP_404_NOT_FOUND)
            list_cohort_id = [cohort.fhir_group_id for cohort in all_user_cohorts if cohort.fhir_group_id]

        cohort_dict_pop_source = get_dict_cohort_pop_source(list_cohort_id)
        return Response(CohortRightsSerializer(get_all_cohorts_rights(user_accesses, cohort_dict_pop_source),
                                               many=True).data)


class NestedCohortResultViewSet(SwaggerSimpleNestedViewSetMixin,
                                CohortResultViewSet):
    def create(self, request, *args, **kwargs):
        if type(request.data) == QueryDict:
            request.data._mutable = True

        if 'request_query_snapshot' in kwargs:
            request.data["request_query_snapshot"] = \
                kwargs['request_query_snapshot']

        return super(NestedCohortResultViewSet, self).create(
            request, *args, **kwargs)
