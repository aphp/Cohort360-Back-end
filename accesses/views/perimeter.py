from django.db.models import Q
from django.http import Http404
from django_filters import rest_framework as filters, OrderingFilter
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_extensions.mixins import NestedViewSetMixin

from admin_cohort.permissions import IsAuthenticatedReadOnly
from admin_cohort.settings import PERIMETERS_TYPES
from admin_cohort.tools import join_qs
from admin_cohort.views import BaseViewset, YarnReadOnlyViewsetMixin, SwaggerSimpleNestedViewSetMixin
from . import swagger_metadata
from ..models import Role, Perimeter, get_user_valid_manual_accesses_queryset, get_all_perimeters_parents_queryset
from ..serializers import PerimeterSerializer, TreefiedPerimeterSerializer, PerimeterLiteSerializer, ReadRightPerimeter
from ..tools.perimeter_process import get_top_perimeter_same_level, get_top_perimeter_inf_level, \
    filter_perimeter_by_top_hierarchy_perimeter_list, filter_accesses_by_search_perimeters, get_read_patient_right, \
    get_top_perimeter_from_read_patient_accesses, is_pseudo_perimeter_in_top_perimeter, \
    is_at_least_one_read_Nomitative_right, get_perimeters_filtered_by_search


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
    ordering = OrderingFilter(fields=(('name', 'care_site_name'),
                                      ('type_source_value', 'care_site_type_source_value'),
                                      ('source_value', 'care_site_source_value')))

    class Meta:
        model = Perimeter
        fields = ("name",
                  "type_source_value",
                  "source_value",
                  "cohort_id",
                  "local_id",
                  "id")


class PerimeterViewSet(YarnReadOnlyViewsetMixin, NestedViewSetMixin, BaseViewset):
    serializer_class = PerimeterSerializer
    queryset = Perimeter.objects.all()
    lookup_field = "id"
    permission_classes = (IsAuthenticatedReadOnly,)

    swagger_tags = ['Accesses - perimeters']
    filterset_class = PerimeterFilter
    search_fields = ["name",
                     "type_source_value",
                     "source_value"]

    @swagger_auto_schema(method='get', operation_summary=swagger_metadata.get_manageable_op_summary,
                         responses={'201': openapi.Response("manageable perimeters found", PerimeterLiteSerializer())})
    @action(detail=False, methods=['get'], url_path="manageable")
    def get_manageable(self, request, *args, **kwargs):
        user_accesses = get_user_valid_manual_accesses_queryset(self.request.user)

        # Get perimeters if search param is used:
        perimeters_filtered_by_search = []
        if self.request.query_params:
            perimeters_filtered_by_search = self.filter_queryset(self.get_queryset())
            if not perimeters_filtered_by_search:
                return Response({"WARN": "No Perimeters Found"})

        if user_accesses.filter(Role.is_manage_role_any_level("role")).count():
            # if edit on any level, we don't care about perimeters' accesses; return the top perimeter hierarchy:
            top_hierarchy_perimeter = Perimeter.objects.filter(parent__isnull=True)
        else:
            access_same_level = [access for access in user_accesses.filter(Role.is_manage_role_same_level("role"))]
            access_inf_level = [access for access in user_accesses.filter(Role.is_manage_role_inf_level("role"))]

            # Get all distinct perimeter from accesses:
            all_perimeters = list(set([access.perimeter for access in access_same_level + access_inf_level]))

            top_perimeter_same_level = list(set(get_top_perimeter_same_level(access_same_level, all_perimeters)))
            top_perimeter_inf_level = get_top_perimeter_inf_level(access_inf_level, all_perimeters,
                                                                  top_perimeter_same_level)

            # Apply Distinct to list
            top_hierarchy_perimeter = list(set(top_perimeter_inf_level + top_perimeter_same_level))

        perimeters = filter_perimeter_by_top_hierarchy_perimeter_list(perimeters_filtered_by_search,
                                                                      top_hierarchy_perimeter)
        return Response(PerimeterLiteSerializer(perimeters, many=True).data)

    @swagger_auto_schema(method='get', operation_summary=swagger_metadata.get_perimeters_read_right_accesses_op_summary,
                         responses=swagger_metadata.get_perimeters_read_right_accesses_responses)
    @action(detail=False, methods=['get'], url_path="read-patient")
    def get_perimeters_read_right_accesses(self, request, *args, **kwargs):
        user_accesses = get_user_valid_manual_accesses_queryset(self.request.user)

        all_read_patient_nominative_accesses = user_accesses.filter(Role.is_read_patient_role_nominative("role"))
        all_read_patient_pseudo_accesses = user_accesses.filter(Role.is_read_patient_role("role"))
        all_read_ipp_accesses = user_accesses.filter(Role.is_search_ipp_role("role"))

        if not all_read_patient_nominative_accesses and not all_read_patient_pseudo_accesses:
            raise Http404("ERROR: No Accesses with read patient right found")
        if self.request.query_params:

            perimeters_filtered_by_search = self.filter_queryset(self.get_queryset())
            if not perimeters_filtered_by_search:
                raise Http404("ERROR: No Perimeters Found")

            return Response(ReadRightPerimeter(
                filter_accesses_by_search_perimeters(perimeters_filtered_by_search,
                                                     all_read_patient_nominative_accesses,
                                                     all_read_patient_pseudo_accesses,
                                                     all_read_ipp_accesses), many=True).data)

        all_distinct_perimeters = get_top_perimeter_from_read_patient_accesses(all_read_patient_nominative_accesses,
                                                                               all_read_patient_pseudo_accesses)

        return Response(ReadRightPerimeter(
            filter_accesses_by_search_perimeters(all_distinct_perimeters,
                                                 all_read_patient_nominative_accesses,
                                                 all_read_patient_pseudo_accesses,
                                                 all_read_ipp_accesses), many=True).data)

    @swagger_auto_schema(method='get',
                         operation_summary="Give boolean read patient pseudo read right for all perimeters searched",
                         responses={'201': openapi.Response("give rights in caresite perimeters found")})
    @action(detail=False, methods=['get'], url_path="is-read-patient-pseudo")
    def get_read_patient_right_access(self, request, *args, **kwargs):
        user_accesses = get_user_valid_manual_accesses_queryset(self.request.user)

        all_read_patient_nominative_accesses = user_accesses.filter(Role.is_read_patient_role_nominative("role"))
        all_read_patient_pseudo_accesses = user_accesses.filter(Role.is_read_patient_role_pseudo("role"))

        if not all_read_patient_nominative_accesses and not all_read_patient_nominative_accesses:
            raise Http404("ERROR No accesses with read patient right Found")
        if self.request.query_params:
            perimeters_filtered_by_search = get_perimeters_filtered_by_search(
                self.request.query_params.get("cohort_id"),
                self.request.user,
                self.filter_queryset(self.get_queryset()))
            if not perimeters_filtered_by_search:
                raise Http404("ERROR No Perimeters Found")
            is_read_patient_pseudo = get_read_patient_right(perimeters_filtered_by_search,
                                                            all_read_patient_nominative_accesses,
                                                            all_read_patient_pseudo_accesses)

            return Response({"is_read_patient_pseudo": is_read_patient_pseudo})

        return Response(
            {"is_read_patient_pseudo": is_pseudo_perimeter_in_top_perimeter(all_read_patient_nominative_accesses,
                                                                            all_read_patient_pseudo_accesses)})

    @swagger_auto_schema(method='get',
                         operation_summary="Give boolean read patient read right (Nomi or Pseudo) on one or "
                                           "several perimeters",
                         responses={'201': openapi.Response("give rights in caresite perimeters found")})
    @action(detail=False, methods=['get'], url_path="is-one-read-patient-right")
    def get_read_one_nominative_patient_right_access(self, request, *args, **kwargs):
        user_accesses = get_user_valid_manual_accesses_queryset(self.request.user)

        all_read_patient_nominative_accesses = user_accesses.filter(Role.is_read_patient_role_nominative("role"))
        all_read_patient_pseudo_accesses = user_accesses.filter(Role.is_read_patient_role_pseudo("role"))

        if not all_read_patient_nominative_accesses and not all_read_patient_nominative_accesses:
            raise Http404("ERROR No accesses with read patient right Found")

        if self.request.query_params:
            perimeters_filtered_by_search = get_perimeters_filtered_by_search(
                self.request.query_params.get("cohort_id"),
                self.request.user,
                self.filter_queryset(self.get_queryset()))
            if not perimeters_filtered_by_search:
                raise Http404("ERROR No Perimeters Found")
            is_read_patient_nominative = is_at_least_one_read_Nomitative_right(perimeters_filtered_by_search,
                                                                               all_read_patient_nominative_accesses,
                                                                               all_read_patient_pseudo_accesses)
            return Response({"is_one_read_nominative_patient_right": is_read_patient_nominative})
        else:
            raise Http404("ERROR at least one search params is required!")

    @swagger_auto_schema(manual_parameters=swagger_metadata.perimeter_list_manual_parameters)
    def list(self, request, *args, **kwargs):
        treefy = request.GET.get("treefy", None)
        if str(treefy).lower() == 'true':
            return self.treefied(request, *args, **kwargs)
        return super(PerimeterViewSet, self).list(request, *args, **kwargs)

    @action(detail=False, methods=['get'], url_path="treefied")
    def treefied(self, request, *args, **kwargs):
        # in that case, for each perimeter filtered, we want to show the
        # branch of the whole perimeter tree that leads to it
        q = self.filter_queryset(self.get_queryset())
        if not q.count():
            return Response([])

        if q.count() != self.get_queryset().count():
            q = (q | get_all_perimeters_parents_queryset(q)).distinct()
            res = q.filter(~Q(parent__id__in=q.values_list("id", flat=True))).distinct()
        else:
            res = q.filter(parent__isnull=True)

        prefetch = Perimeter.children_prefetch(q)
        for _ in range(2, len(PERIMETERS_TYPES)):
            prefetch = Perimeter.children_prefetch(q.prefetch_related(prefetch))

        res = res.prefetch_related(prefetch)
        return Response(TreefiedPerimeterSerializer(res, many=True).data)


class NestedPerimeterViewSet(SwaggerSimpleNestedViewSetMixin, PerimeterViewSet):
    @swagger_auto_schema(auto_schema=None)
    def get_manageable(self, request, *args, **kwargs):
        return super(NestedPerimeterViewSet, self).get_manageable(request, *args, **kwargs)

    def treefied(self, request, *args, **kwargs):
        return super(NestedPerimeterViewSet, self).treefied(request, *args, **kwargs)
