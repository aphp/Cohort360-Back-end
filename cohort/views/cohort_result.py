from django.db import transaction
from django.db.models import Q
from django_filters import rest_framework as filters, OrderingFilter
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_extensions.mixins import NestedViewSetMixin

from admin_cohort.tools.cache import cache_response
from admin_cohort.tools import join_qs
from cohort.services.cohort_result import cohort_service
from cohort.models import CohortResult
from cohort.serializers import CohortResultSerializer, CohortResultCreateSerializer, CohortResultPatchSerializer, CohortRightsSerializer
from cohort.services.cohort_rights import cohort_rights_service
from cohort.views.shared import UserObjectsRestrictedViewSet
from exports.services.export import export_service


class CohortFilter(filters.FilterSet):

    def multi_value_filter(self, queryset, field, value: str):
        if value:
            sub_values = [val.strip() for val in value.split(",")]
            return queryset.filter(join_qs([Q(**{field: v}) for v in sub_values]))
        return queryset

    name = filters.CharFilter(field_name='name', lookup_expr="icontains")
    min_result_size = filters.NumberFilter(field_name='dated_measure__measure', lookup_expr='gte')
    max_result_size = filters.NumberFilter(field_name='dated_measure__measure', lookup_expr='lte')
    min_created_at = filters.IsoDateTimeFilter(field_name='created_at', lookup_expr="gte")
    max_created_at = filters.IsoDateTimeFilter(field_name='created_at', lookup_expr="lte")
    request_id = filters.CharFilter(field_name='request_query_snapshot__request__pk')
    group_id = filters.CharFilter(method="multi_value_filter", field_name="group_id")
    status = filters.CharFilter(method="multi_value_filter", field_name="request_job_status")

    ordering = OrderingFilter(fields=('-created_at',
                                      'modified_at',
                                      'name',
                                      ('dated_measure__measure', 'result_size'),
                                      'favorite'))

    class Meta:
        model = CohortResult
        fields = ('name',
                  'min_result_size',
                  'max_result_size',
                  'min_created_at',
                  'max_created_at',
                  'request_id',
                  'favorite',
                  'group_id',
                  'status')


class CohortResultViewSet(NestedViewSetMixin, UserObjectsRestrictedViewSet):
    queryset = CohortResult.objects.select_related('dated_measure',
                                                   'dated_measure_global',
                                                   'request_query_snapshot__request')
    serializer_class = CohortResultSerializer
    http_method_names = ['get', 'post', 'patch', 'delete']
    swagger_tags = ["Cohorts"]
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


    @cache_response()
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


    @extend_schema(request=CohortResultCreateSerializer, responses={status.HTTP_201_CREATED: CohortResultSerializer})
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        global_estimate = request.data.pop("global_estimate", False)
        response = super().create(request, *args, **kwargs)
        transaction.on_commit(lambda: cohort_service.handle_cohort_creation(request=request,
                                                                            cohort=response.data.serializer.instance,
                                                                            global_estimate=global_estimate))
        return response


    @extend_schema(request=CohortResultPatchSerializer, responses={status.HTTP_200_OK: CohortResultSerializer})
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


    @action(methods=['get'], detail=False, url_path='jobs/active')
    def get_active_jobs(self, request, *args, **kwargs):
        return Response(data={"jobs_count": cohort_service.count_active_jobs()},
                        status=status.HTTP_200_OK)


    @extend_schema(responses={status.HTTP_200_OK: CohortRightsSerializer(many=True)})
    @action(detail=False, methods=['get'], url_path="cohort-rights")
    def get_rights_on_cohorts(self, request, *args, **kwargs):
        cohorts_rights = cohort_rights_service.get_user_rights_on_cohorts(group_ids=request.query_params.get('group_id'),
                                                                          user=request.user)
        serializer = CohortRightsSerializer(data=cohorts_rights, many=True)
        serializer.is_valid()
        return Response(data=serializer.data,
                        status=status.HTTP_200_OK)
