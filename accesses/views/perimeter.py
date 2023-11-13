from functools import reduce

from django.db.models import Q
from django_filters import rest_framework as filters, OrderingFilter
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_extensions.mixins import NestedViewSetMixin

from admin_cohort.tools.cache import cache_response
from admin_cohort.permissions import IsAuthenticatedReadOnly, user_is_full_admin
from admin_cohort.tools import join_qs
from admin_cohort.tools.negative_limit_paginator import NegativeLimitOffsetPagination
from admin_cohort.views import BaseViewset
from accesses.models import Role, Perimeter
from accesses.tools import get_user_valid_manual_accesses, get_top_manageable_perimeters
from accesses.serializers import PerimeterSerializer, PerimeterLiteSerializer, DataReadRightSerializer, ReadRightPerimeter
from accesses.utils.perimeter_process import get_perimeters_read_rights, get_read_patient_right, \
    is_pseudo_perimeter_in_top_perimeter, has_at_least_one_read_nominative_right, \
    get_read_nominative_boolean_from_specific_logic_function, get_all_read_patient_accesses, get_read_opposing_patient_accesses, \
    get_top_perimeters_with_right_read_nomi, get_top_perimeters_with_right_read_pseudo, get_data_reading_rights_on_perimeters


class PerimeterFilter(filters.FilterSet):

    def multi_value_filter(self, queryset, field, field_value: str):
        if field_value:
            strip_field_values = [value.strip() for value in field_value.split(",")]
            return queryset.filter(join_qs([Q(**{field: value}) for value in strip_field_values]))
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

    @swagger_auto_schema(method='get',
                         operation_summary="Get the top hierarchy perimeters on which the user has at least one role that allows to give accesses."
                                           "-Same level rights give access to a perimeter and its lower levels."   # todo: should be same level only
                                           "-Inferior level rights give only access to children of a perimeter.",
                         responses={'200': openapi.Response("manageable perimeters found", PerimeterLiteSerializer())})
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

    @swagger_auto_schema(method='get',
                         operation_summary="Return perimeters and associated read patient's data rights for current user.",
                         responses={'200': openapi.Response("Rights per perimeter", ReadRightPerimeter())})
    @action(detail=False, methods=['get'], url_path="read-patient")
    @cache_response()
    def get_data_reading_rights_on_perimeters(self, request, *args, **kwargs):
        data_reading_rights = get_data_reading_rights_on_perimeters(user=request.user,
                                                                    target_perimeters=self.filter_queryset(self.queryset))
        page = self.paginate_queryset(data_reading_rights)
        if page:
            serializer = ReadRightPerimeter(page, many=True)
            return self.get_paginated_response(serializer.data)
        return Response(data={}, status=status.HTTP_200_OK)

    @swagger_auto_schema(method='get',
                         operation_summary="Whether or not the user has a `read patient data in pseudo mode` right for all searched perimeters",
                         responses={'200': openapi.Response("Return is_read_patient_pseudo boolean")})
    @action(detail=False, methods=['get'], url_path="is-read-patient-pseudo")
    @cache_response()
    def get_read_patient_pseudo_right(self, request, *args, **kwargs):
        all_read_patient_nominative_accesses, all_read_patient_pseudo_accesses = get_all_read_patient_accesses(request.user)
        is_opposing_patient_read = get_read_opposing_patient_accesses(request.user)
        if request.query_params:
            is_read_patient_nominative = get_read_nominative_boolean_from_specific_logic_function(request,
                                                                                                  self.filter_queryset(self.get_queryset()),
                                                                                                  all_read_patient_nominative_accesses,
                                                                                                  all_read_patient_pseudo_accesses,
                                                                                                  get_read_patient_right)
            is_read_patient_pseudo = not is_read_patient_nominative
        else:
            is_read_patient_pseudo = is_pseudo_perimeter_in_top_perimeter(all_read_patient_nominative_accesses,
                                                                          all_read_patient_pseudo_accesses)

        return Response(data={"is_read_patient_pseudo": is_read_patient_pseudo,
                              "is_opposing_patient_read": is_opposing_patient_read
                              }, status=status.HTTP_200_OK)

    @swagger_auto_schema(method='get',
                         operation_summary="whether or not the user has a `read patient data in nominative mode` right on one or several perimeters",
                         responses={'200': openapi.Response("give rights in perimeters found")})
    @action(detail=False, methods=['get'], url_path="is-one-read-patient-right")
    @cache_response()
    def get_read_one_nominative_patient_right_access(self, request, *args, **kwargs):
        all_read_patient_nominative_accesses, all_read_patient_pseudo_accesses = get_all_read_patient_accesses(request.user)
        is_opposing_patient_read = get_read_opposing_patient_accesses(request.user)
        if request.query_params:
            is_read_patient_nominative = get_read_nominative_boolean_from_specific_logic_function(request,
                                                                                                  self.filter_queryset(self.get_queryset()),
                                                                                                  all_read_patient_nominative_accesses,
                                                                                                  all_read_patient_pseudo_accesses,
                                                                                                  has_at_least_one_read_nominative_right)
            return Response(data={"is_one_read_nominative_patient_right": is_read_patient_nominative,
                                  "is_opposing_patient_read": is_opposing_patient_read},
                            status=status.HTTP_200_OK)
        else:
            return Response(data="At least one search parameter is required", status=status.HTTP_400_BAD_REQUEST)


class NestedPerimeterViewSet(PerimeterViewSet):
    pass
