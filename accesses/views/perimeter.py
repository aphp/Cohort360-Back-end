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
from admin_cohort.permissions import IsAuthenticatedReadOnly
from admin_cohort.tools import join_qs
from admin_cohort.tools.negative_limit_paginator import NegativeLimitOffsetPagination
from admin_cohort.views import BaseViewSet
from accesses.services.accesses import accesses_service
from accesses.services.perimeters import perimeters_service
from accesses.models import Perimeter
from accesses.serializers import PerimeterSerializer, PerimeterLiteSerializer, ReadRightPerimeter

MAX, MIN = 'max', 'min'


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


class PerimeterViewSet(NestedViewSetMixin, BaseViewSet):
    serializer_class = PerimeterSerializer
    queryset = Perimeter.objects.all()
    lookup_field = "id"
    http_method_names = ["get"]
    permission_classes = [IsAuthenticatedReadOnly]
    pagination_class = NegativeLimitOffsetPagination
    swagger_tags = ['Accesses - perimeters']
    filterset_class = PerimeterFilter
    search_fields = ["name",
                     "type_source_value",
                     "source_value"]

    @swagger_auto_schema(manual_parameters=
                         list(map(lambda x: openapi.Parameter(name=x[0], description=x[1], type=x[2],
                                                              pattern=x[3] if len(x) == 4 else None, in_=openapi.IN_QUERY),
                                  [["ordering", "'field' or '-field': name, type_source_value, source_value", openapi.TYPE_STRING],
                                   ["search", "Based on: name, type_source_value, source_value", openapi.TYPE_STRING]])))
    @cache_response()
    def list(self, request, *args, **kwargs):
        return super(PerimeterViewSet, self).list(request, *args, **kwargs)

    @swagger_auto_schema(operation_summary="Get the top hierarchy perimeters on which the user has at least "
                                           "one role that allows to give accesses."
                                           "-Same level rights give access to a perimeter and its lower levels."
                                           "-Inferior level rights give only access to children of a perimeter.",
                         responses={'200': openapi.Response("Manageable perimeters", PerimeterLiteSerializer())})
    @action(detail=False, methods=['get'], url_path="manageable")
    @cache_response()
    def get_manageable_perimeters(self, request, *args, **kwargs):
        manageable_perimeters = perimeters_service.get_top_manageable_perimeters(user=request.user)
        if request.query_params:
            manageable_perimeters_children = reduce(lambda qs1, qs2: qs1.union(qs2),
                                                    [perimeters_service.get_all_child_perimeters(perimeter=p)
                                                     for p in manageable_perimeters])
            manageable_perimeters = manageable_perimeters | manageable_perimeters_children
            manageable_perimeters = self.filter_queryset(queryset=manageable_perimeters)
        return Response(data=PerimeterLiteSerializer(manageable_perimeters, many=True).data,
                        status=status.HTTP_200_OK)

    @swagger_auto_schema(operation_summary="Return a patient-data-reading-rights summary on target perimeters.",
                         responses={'200': openapi.Response("Rights per perimeter", ReadRightPerimeter())})
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

    @swagger_auto_schema(operation_summary="Return if the user has the right to read patient data in nomi or pseudo "
                                           "mode on at least one perimeter, and if allowed to read opposed patients data",
                         responses={'200': openapi.Response("Return 2 booleans describing user's data rights")})
    @action(detail=False, methods=['get'], url_path="patient-data/read")
    @cache_response()
    def check_read_patient_data_rights(self, request, *args, **kwargs):
        user = request.user
        cohort_ids = request.query_params.get("cohort_ids")
        read_mode = request.query_params.get('mode')
        if read_mode not in (MAX, MIN):
            return Response(data={"error": "Patient data reading `mode` is missing or has invalid value"},
                            status=status.HTTP_400_BAD_REQUEST)
        target_perimeters = self.queryset
        if accesses_service.is_user_allowed_unlimited_patients_read(user=user):
            data = {"allow_read_patient_data_nomi": True,
                    "allow_lookup_opposed_patients": True,
                    "allow_read_patient_without_perimeter_limit": True
                    }
            return Response(data=data, status=status.HTTP_200_OK)

        if cohort_ids:
            target_perimeters = perimeters_service.get_target_perimeters(cohort_ids=cohort_ids, owner=user)
        target_perimeters = self.filter_queryset(target_perimeters)

        if not target_perimeters:
            return Response(data={"error": "None of the target perimeters was found"}, status=status.HTTP_404_NOT_FOUND)

        if not accesses_service.user_has_data_reading_accesses_on_target_perimeters(user=user,
                                                                                    target_perimeters=target_perimeters,
                                                                                    read_mode=read_mode):
            return Response(data={"error": "User has no data reading accesses"}, status=status.HTTP_404_NOT_FOUND)

        if read_mode == MAX:
            allow_read_patient_data_nomi = accesses_service \
                .user_can_access_at_least_one_target_perimeter_in_nomi(user=user, target_perimeters=target_perimeters)
        else:
            allow_read_patient_data_nomi = accesses_service.user_can_access_all_target_perimeters_in_nomi(user=user,
                                                                                                          target_perimeters=target_perimeters)
        data = {"allow_read_patient_data_nomi": allow_read_patient_data_nomi,
                "allow_lookup_opposed_patients": accesses_service.can_user_read_opposed_patient_data(user=user),
                "allow_read_patient_without_perimeter_limit": False
                }
        return Response(data=data, status=status.HTTP_200_OK)


class NestedPerimeterViewSet(PerimeterViewSet):
    pass
