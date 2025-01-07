from functools import reduce

from django.db.models import Q
from django_filters import rest_framework as filters, OrderingFilter
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_extensions.mixins import NestedViewSetMixin

from admin_cohort.tools import join_qs
from admin_cohort.tools.cache import cache_response
from admin_cohort.tools.negative_limit_paginator import NegativeLimitOffsetPagination
from accesses.permissions import IsAuthenticatedReadOnly
from accesses.views import BaseViewSet
from accesses.services.accesses import accesses_service
from accesses.services.perimeters import perimeters_service
from accesses.models import Perimeter
from accesses.serializers import PerimeterSerializer, PerimeterLiteSerializer, ReadRightPerimeter, RightReadPatientDataSerializer

MAX, MIN = 'max', 'min'


class PerimeterFilter(filters.FilterSet):

    def multi_value_filter(self, queryset, field, field_value: str):
        if field_value:
            values = [value.strip() for value in field_value.split(",")]
            return queryset.filter(join_qs([Q(**{field: value}) for value in values]))
        return queryset

    name = filters.CharFilter(lookup_expr='icontains')
    type_source_value = filters.CharFilter(method="multi_value_filter", field_name="type_source_value")
    source_value = filters.CharFilter(lookup_expr='icontains')
    cohort_id = filters.CharFilter(method="multi_value_filter", field_name="cohort_id")
    parent_id = filters.CharFilter(method="multi_value_filter", field_name="parent_id")
    local_id = filters.CharFilter(method="multi_value_filter", field_name="local_id")
    ordering = OrderingFilter(fields=(('name', 'care_site_name'),
                                      ('type_source_value', 'care_site_type_source_value'),
                                      ('source_value', 'care_site_source_value')))

    class Meta:
        model = Perimeter
        fields = ("name",
                  "type_source_value",
                  "source_value",
                  "cohort_id",
                  "parent_id",
                  "local_id")


class PerimeterViewSet(NestedViewSetMixin, BaseViewSet):
    serializer_class = PerimeterSerializer
    queryset = Perimeter.objects.all()
    lookup_field = "id"
    http_method_names = ["get"]
    permission_classes = [IsAuthenticatedReadOnly]
    pagination_class = NegativeLimitOffsetPagination
    swagger_tags = ['Perimeters']
    filterset_class = PerimeterFilter
    search_fields = ["name",
                     "type_source_value",
                     "source_value"]

    @extend_schema(responses={status.HTTP_200_OK: PerimeterSerializer(many=True)})
    @cache_response()
    def list(self, request, *args, **kwargs):
        return super(PerimeterViewSet, self).list(request, *args, **kwargs)

    @extend_schema(responses={status.HTTP_200_OK: PerimeterLiteSerializer(many=True)})
    @action(detail=False, methods=['get'], url_path="manageable")
    @cache_response()
    def get_manageable_perimeters(self, request, *args, **kwargs):
        manageable_perimeters = perimeters_service.get_top_manageable_perimeters(user=request.user)
        if request.query_params:
            manageable_perimeters_children = reduce(lambda qs1, qs2: qs1.union(qs2),
                                                    [perimeters_service.get_all_child_perimeters(perimeter_id=p.id)
                                                     for p in manageable_perimeters])
            manageable_perimeters = manageable_perimeters | manageable_perimeters_children
            manageable_perimeters = self.filter_queryset(queryset=manageable_perimeters)
        return Response(data=PerimeterLiteSerializer(manageable_perimeters, many=True).data,
                        status=status.HTTP_200_OK)

    @extend_schema(responses={status.HTTP_200_OK: ReadRightPerimeter})
    @action(detail=False, methods=['get'], url_path="patient-data/rights")
    @cache_response()
    def get_data_read_rights_on_perimeters(self, request, *args, **kwargs):
        filtered_perimeters = self.filter_queryset(self.queryset)
        data_reading_rights = perimeters_service.get_data_read_rights_on_perimeters(user=request.user,
                                                                                    is_request_filtered=bool(request.query_params),
                                                                                    filtered_perimeters=filtered_perimeters)
        page = self.paginate_queryset(data_reading_rights)
        if page:
            serializer = ReadRightPerimeter(page, many=True)
            return self.get_paginated_response(serializer.data)
        return Response(data={}, status=status.HTTP_200_OK)

    @extend_schema(parameters=[OpenApiParameter("cohort_ids", OpenApiTypes.STR,
                                                description="Comma separated list of perimeters cohort_id"),
                               OpenApiParameter("mode", OpenApiTypes.STR, description="Values: min, max")],
                   responses={status.HTTP_200_OK: RightReadPatientDataSerializer,
                              status.HTTP_400_BAD_REQUEST: None})
    @action(detail=False, methods=['get'], url_path="patient-data/read")
    @cache_response()
    def check_read_patient_data_rights(self, request, *args, **kwargs):
        """
        cohort_ids: comma separated IDs that may refer to `cohort.group_id` or `perimeter.cohort_id`
        mode=min:
            * all perimeters must be accessible otherwise return HTTP404
            * all perimeters must be accessible in nominative mode else: allow_read_patient_data_nomi = False
        mode=max:
            * at least one perimeter must be accessible otherwise return HTTP404
            * at least one perimeter must be accessible in nominative mode else: allow_read_patient_data_nomi = False
        """
        user = request.user
        cohort_ids = request.query_params.get("cohort_ids")
        read_mode = request.query_params.get('mode')
        if cohort_ids is None:
            return Response(data={"error": "Missing `cohort_ids` parameter"}, status=status.HTTP_400_BAD_REQUEST)
        if read_mode not in (MAX, MIN):
            return Response(data={"error": "Patient data reading `mode` is missing or has invalid value"}, status=status.HTTP_400_BAD_REQUEST)

        if accesses_service.is_user_allowed_unlimited_patients_read(user=user):
            serializer = RightReadPatientDataSerializer(data={"allow_read_patient_data_nomi": True,
                                                              "allow_lookup_opposed_patients": True,
                                                              "allow_read_patient_without_perimeter_limit": True
                                                              })
            serializer.is_valid()
            return Response(data=serializer.data, status=status.HTTP_200_OK)

        target_perimeters = perimeters_service.get_target_perimeters(cohort_ids=cohort_ids)

        if not target_perimeters.exists():
            return Response(data={"error": "None of the target perimeters was found"}, status=status.HTTP_404_NOT_FOUND)

        if not accesses_service.user_has_data_reading_accesses_on_target_perimeters(user=user,
                                                                                    target_perimeters=target_perimeters,
                                                                                    read_mode=read_mode):
            return Response(data={"error": "User has no data reading accesses"}, status=status.HTTP_404_NOT_FOUND)

        if read_mode == MAX:
            allow_read_patient_data_nomi = accesses_service.user_can_access_at_least_one_target_perimeter_in_nomi(user=user,
                                                                                                                  target_perimeters=target_perimeters)
        else:
            allow_read_patient_data_nomi = accesses_service.user_can_access_all_target_perimeters_in_nomi(user=user,
                                                                                                          target_perimeters=target_perimeters)
        serializer = RightReadPatientDataSerializer(
            data={"allow_read_patient_data_nomi": allow_read_patient_data_nomi,
                  "allow_lookup_opposed_patients": accesses_service.can_user_read_opposed_patient_data(user=user),
                  "allow_read_patient_without_perimeter_limit": False
                  })
        serializer.is_valid()
        return Response(data=serializer.data, status=status.HTTP_200_OK)


class NestedPerimeterViewSet(PerimeterViewSet):
    pass
