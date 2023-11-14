from functools import reduce

from django.db.models import Q
from django.http import Http404
from django_filters import rest_framework as filters, OrderingFilter
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_extensions.mixins import NestedViewSetMixin

from admin_cohort.tools.cache import cache_response
from admin_cohort.permissions import IsAuthenticatedReadOnly
from admin_cohort.tools import join_qs
from admin_cohort.tools.negative_limit_paginator import NegativeLimitOffsetPagination
from admin_cohort.views import BaseViewset
from accesses.models import Perimeter
from accesses.tools import get_top_manageable_perimeters, get_data_reading_rights_on_perimeters, \
    get_target_perimeters, check_user_can_read_patient_data_in_nomi, \
    check_user_can_read_patient_data_in_pseudo, check_user_can_read_opposed_patient_data
from accesses.serializers import PerimeterSerializer, PerimeterLiteSerializer, ReadRightPerimeter


class PerimeterFilter(filters.FilterSet):

    def multi_value_filter(self, queryset, field, field_value: str):
        if field_value:
            values = [value.strip() for value in field_value.split(",")]
            return queryset.filter(join_qs([Q(**{field: value}) for value in values]))
        return queryset

    name = filters.CharFilter(lookup_expr='icontains')
    source_value = filters.CharFilter(lookup_expr='icontains')
    cohort_id = filters.CharFilter(method="multi_value_filter", field_name="cohort_id")
    local_id = filters.CharFilter(method="multi_value_filter", field_name="local_id")
    parent_id = filters.CharFilter(method="multi_value_filter", field_name="parent_id")
    type_source_value = filters.CharFilter(method="multi_value_filter", field_name="type_source_value")
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
                  "local_id",
                  "id")


class PerimeterViewSet(NestedViewSetMixin, BaseViewset):
    serializer_class = PerimeterSerializer
    queryset = Perimeter.objects.all()
    lookup_field = "id"
    http_method_names = ["get"]
    permission_classes = (IsAuthenticatedReadOnly,)
    pagination_class = NegativeLimitOffsetPagination
    swagger_tags = ['Accesses - perimeters']
    filterset_class = PerimeterFilter
    search_fields = ["name",
                     "type_source_value",
                     "source_value"]

    @swagger_auto_schema(manual_parameters=list(map(lambda x: openapi.Parameter(name=x[0], description=x[1], type=x[2],
                                                                                pattern=x[3] if len(x) == 4 else None, in_=openapi.IN_QUERY),
                                                    [["ordering", "'field' or '-field': name, type_source_value, source_value", openapi.TYPE_STRING],
                                                     ["search", "Based on: name, type_source_value, source_value", openapi.TYPE_STRING]])))
    @cache_response()
    def list(self, request, *args, **kwargs):
        return super(PerimeterViewSet, self).list(request, *args, **kwargs)

    @swagger_auto_schema(operation_summary="Get the top hierarchy perimeters on which the user has at least one role that allows to give accesses."
                                           "-Same level rights give access to a perimeter and its lower levels."   # todo: should be same level only
                                           "-Inferior level rights give only access to children of a perimeter.",
                         method='GET', responses={'200': openapi.Response("manageable perimeters found", PerimeterLiteSerializer())})
    @action(detail=False, methods=['get'], url_path="manageable")
    @cache_response()
    def get_manageable_perimeters(self, request, *args, **kwargs):
        manageable_perimeters = get_top_manageable_perimeters(user=request.user)
        if request.query_params:
            manageable_perimeters_children = reduce(lambda qs1, qs2: qs1.union(qs2),
                                                    [p.all_children for p in manageable_perimeters])
            all_manageable_perimeters = manageable_perimeters.union(manageable_perimeters_children)
            manageable_perimeters = self.filter_queryset(queryset=all_manageable_perimeters)
        return Response(data=PerimeterLiteSerializer(manageable_perimeters, many=True).data,
                        status=status.HTTP_200_OK)

    @swagger_auto_schema(operation_summary="Return perimeters and associated read patient's data rights for current user.",
                         method='GET', responses={'200': openapi.Response("Rights per perimeter", ReadRightPerimeter())})
    @action(detail=False, methods=['get'], url_path="patient-data-reading-rights")
    @cache_response()
    def get_data_reading_rights_on_perimeters(self, request, *args, **kwargs):
        # todo: [front] update route "/perimeters/read-patient/"
        data_reading_rights = get_data_reading_rights_on_perimeters(user=request.user,
                                                                    target_perimeters=self.filter_queryset(self.queryset))
        page = self.paginate_queryset(data_reading_rights)
        if page:
            serializer = ReadRightPerimeter(page, many=True)
            return self.get_paginated_response(serializer.data)
        return Response(data={}, status=status.HTTP_200_OK)

    @swagger_auto_schema(operation_summary="Return if the user has a `read patient data in nominative mode` right on at least one perimeter",
                         method='GET', responses={'200': openapi.Response("Return 2 booleans describing user's rights")})
    @action(detail=False, methods=['get'], url_path="allow-read-patient-nomi")
    @cache_response()
    def get_read_patient_data_nomi_right(self, request, *args, **kwargs):
        # todo: [FHIR] update route "/perimeters/is-one-read-patient-right/"
        # todo: [FHIR] update response keys
        if not request.query_params:
            return Response(data="At least one search parameter is required",   # todo: ask Nico why ?
                            status=status.HTTP_400_BAD_REQUEST)
        target_perimeters = self.queryset
        if request.query_params.get("cohort_id"):
            target_perimeters = get_target_perimeters(cohort_ids=request.query_params.get("cohort_id"),
                                                      owner=request.user)
        target_perimeters = self.filter_queryset(target_perimeters)
        if not target_perimeters:
            raise Http404("Error: None of the target perimeters was found")

        allow_read_patient_data_nomi = check_user_can_read_patient_data_in_nomi(user=request.user, target_perimeters=target_perimeters)
        allow_read_opposed_patient_data = check_user_can_read_opposed_patient_data(user=request.user)
        return Response(data={"allow_read_patient_data_nomi": allow_read_patient_data_nomi,
                              "allow_read_opposing_patient_data": allow_read_opposed_patient_data},
                        status=status.HTTP_200_OK)

    @swagger_auto_schema(operation_summary="Whether or not the user has a `read patient data in pseudo mode` right on target perimeters",
                         method='GET', responses={'200': openapi.Response("Return 2 booleans describing user's rights")})
    @action(detail=False, methods=['get'], url_path="allow-read-patient-pseudo")
    @cache_response()
    def get_read_patient_data_pseudo_right(self, request, *args, **kwargs):
        # todo: [FHIR] update route "/perimeters/is-read-patient-pseudo/"
        # todo: [FHIR] update response keys
        target_perimeters = self.queryset
        if request.query_params.get("cohort_id"):
            target_perimeters = get_target_perimeters(cohort_ids=request.query_params.get("cohort_id"),
                                                      owner=request.user)
        target_perimeters = self.filter_queryset(target_perimeters)
        if not target_perimeters:
            return Response(data="Error: None of the target perimeters was found", status=status.HTTP_404_NOT_FOUND)

        allow_read_patient_data_pseudo = check_user_can_read_patient_data_in_pseudo(user=request.user, target_perimeters=target_perimeters)
        allow_read_opposed_patient_data = check_user_can_read_opposed_patient_data(user=request.user)
        return Response(data={"allow_read_patient_data_pseudo": allow_read_patient_data_pseudo,
                              "allow_read_opposing_patient_data": allow_read_opposed_patient_data},
                        status=status.HTTP_200_OK)


class NestedPerimeterViewSet(PerimeterViewSet):
    pass
