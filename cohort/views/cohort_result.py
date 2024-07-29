from django.db import transaction
from django.db.models import Q, F
from django_filters import rest_framework as filters, OrderingFilter
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_extensions.mixins import NestedViewSetMixin

from admin_cohort.tools.cache import cache_response
from admin_cohort.tools import join_qs
from admin_cohort.tools.negative_limit_paginator import NegativeLimitOffsetPagination
from cohort.services.cohort_result import cohort_service
from cohort.models import CohortResult
from cohort.serializers import CohortResultSerializer, CohortResultSerializerFullDatedMeasure, CohortResultCreateSerializer, \
    CohortResultPatchSerializer, CohortRightsSerializer
from cohort.services.cohort_rights import cohort_rights_service
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
    swagger_tags = ['Cohorts']
    pagination_class = NegativeLimitOffsetPagination
    filterset_class = CohortFilter
    search_fields = ('$name', '$description')
    non_updatable_fields = ['owner', 'owner_id',
                            'request_query_snapshot', 'request_query_snapshot_id',
                            'dated_measure', 'dated_measure_id']

    def get_permissions(self):
        special_permissions = cohort_service.get_special_permissions(self.request)
        if special_permissions:
            return special_permissions
        if self.action == self.get_active_jobs.__name__:
            return [AllowAny()]
        return super().get_permissions()

    def get_queryset(self):
        if cohort_service.allow_use_full_queryset(request=self.request):
            return self.queryset
        return super().get_queryset().filter(is_subset=False)

    def get_serializer_class(self):
        if self.request.method in ["POST", "PUT", "PATCH"] \
                and "dated_measure" in self.request.data \
                and isinstance(self.request.data["dated_measure"], dict) \
                or self.request.method == "GET":
            return CohortResultSerializerFullDatedMeasure
        return self.serializer_class

    @extend_schema(tags=swagger_tags,
                   responses={status.HTTP_200_OK: None})
    @action(methods=['get'], detail=False, url_path='jobs/active')
    def get_active_jobs(self, request, *args, **kwargs):
        return Response(data={"jobs_count": cohort_service.count_active_jobs()},
                        status=status.HTTP_200_OK)

    @extend_schema(tags=swagger_tags,
                   responses={status.HTTP_200_OK: CohortResultSerializer})
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(tags=swagger_tags,
                   responses={status.HTTP_200_OK: CohortResultSerializer})
    @cache_response()
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(tags=swagger_tags,
                   request=CohortResultCreateSerializer,
                   responses={status.HTTP_201_CREATED: CohortResultSerializer})
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        transaction.on_commit(lambda: cohort_service.handle_cohort_creation(request=request,
                                                                            cohort=response.data.serializer.instance))
        return response

    @extend_schema(tags=swagger_tags,
                   request=CohortResultPatchSerializer,
                   responses={status.HTTP_200_OK: CohortResultSerializer})
    def partial_update(self, request, *args, **kwargs):
        if any(field in self.non_updatable_fields for field in request.data):
            return Response(data=f"The payload contains non-updatable fields `{request.data}`",
                            status=status.HTTP_400_BAD_REQUEST)
        cohort = self.get_object()
        try:
            cohort_service.handle_patch_cohort(cohort=cohort, data=request.data)
        except ValueError as ve:
            cohort_service.mark_cohort_as_failed(cohort=cohort, reason=str(ve))
            response = Response(data=str(ve), status=status.HTTP_400_BAD_REQUEST)
        else:
            response = super().partial_update(request, *args, **kwargs)
            cohort_service.handle_cohort_post_update(cohort=cohort, data=request.data)
            if cohort.export_table.exists():
                export_service.check_all_cohort_subsets_created(export=cohort.export_table.first().export)
        cohort_service.ws_send_to_client(cohort=cohort)
        return response

    @extend_schema(tags=swagger_tags,
                   responses={status.HTTP_204_NO_CONTENT: None})
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    @extend_schema(tags=swagger_tags,
                   responses={status.HTTP_200_OK: CohortRightsSerializer})
    @action(detail=False, methods=['get'], url_path="cohort-rights")
    def get_rights_on_cohorts(self, request, *args, **kwargs):
        cohorts_rights = cohort_rights_service.get_user_rights_on_cohorts(group_ids=request.query_params.get('group_id'),
                                                                          user=request.user)
        return Response(data=CohortRightsSerializer(data=cohorts_rights, many=True).data,
                        status=status.HTTP_200_OK)
