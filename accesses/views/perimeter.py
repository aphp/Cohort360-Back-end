from django.db.models import Q
from django_filters import rest_framework as filters, OrderingFilter
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_extensions.mixins import NestedViewSetMixin

from admin_cohort.permissions import IsAuthenticatedReadOnly
from admin_cohort.settings import PERIMETERS_TYPES
from admin_cohort.views import BaseViewset, YarnReadOnlyViewsetMixin, \
    SwaggerSimpleNestedViewSetMixin
from ..models import Role, Perimeter, get_user_valid_manual_accesses_queryset, \
    get_all_perimeters_parents_queryset
from ..serializers import PerimeterSerializer, \
    TreefiedPerimeterSerializer, YasgTreefiedPerimeterSerializer, PerimeterLiteSerializer, AccessSerializer
from ..tools.perimeter_process import get_top_perimeter_same_level, get_top_perimeter_inf_level, \
    filter_perimeter_by_top_hierarchy_perimeter_list, get_top_accesses_nominative, get_top_accesses_pseudo


class PerimeterFilter(filters.FilterSet):
    name = filters.CharFilter(lookup_expr='icontains')
    source_value = filters.CharFilter(lookup_expr='icontains')

    ordering = OrderingFilter(fields=(('name', 'care_site_name'),
                                      ('type_source_value', 'care_site_type_source_value'),
                                      ('source_value', 'care_site_source_value')))

    class Meta:
        model = Perimeter
        fields = (
            "name",
            "type_source_value",
            "source_value",
            "id",
        )


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

    @swagger_auto_schema(
        method='get',
        operation_summary="Get the top hierarchy perimeters on which the user has at least "
                          "one role that allows to give accesses."
                          "- Same level right give access to current perimeter and lower levels."
                          "- Inferior level right give only access to children of current perimeter.",
        responses={
            '201': openapi.Response("manageable perimeters found",
                                    PerimeterLiteSerializer()
                                    ),
        }
    )
    @action(detail=False, methods=['get'], url_path="manageable")
    def get_manageable(self, request, *args, **kwargs):
        user_accesses = get_user_valid_manual_accesses_queryset(
            self.request.user)

        # Get perimeters if search param is used:
        perimeters_filtered_by_search = []
        if len(self.request.query_params) > 0:
            perimeters_filtered_by_search = self.filter_queryset(self.get_queryset())
            if len(perimeters_filtered_by_search) == 0:
                return Response({"WARN": "No Perimeters Found"})

        if user_accesses.filter(Role.is_manage_role_any_level("role")).count():
            # if edit on any level, we don't care about perimeters' accesses; return the top perimeter hierarchy:
            top_hierarchy_perimeter = Perimeter.objects.filter(parent__isnull=True)
            return Response(PerimeterLiteSerializer(
                filter_perimeter_by_top_hierarchy_perimeter_list(perimeters_filtered_by_search,
                                                                 top_hierarchy_perimeter), many=True).data)
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

        return Response(
            PerimeterLiteSerializer(filter_perimeter_by_top_hierarchy_perimeter_list(perimeters_filtered_by_search,
                                                                                     top_hierarchy_perimeter),
                                    many=True).data)

    @swagger_auto_schema(
        method='get',
        operation_summary="Get the top hierarchy perimeters on which the user has at least "
                          "one role that allows to give accesses."
                          "- Same level right give access to current perimeter and lower levels."
                          "- Inferior level right give only access to children of current perimeter.",
        responses={
            '201': openapi.Response("manageable perimeters found",
                                    PerimeterLiteSerializer()
                                    ),
        }
    )
    @action(detail=False, methods=['get'], url_path="top-hierarchy/read-patient")
    def get_top_read_right_accesses(self, request, *args, **kwargs):
        user_accesses = get_user_valid_manual_accesses_queryset(self.request.user)

        nominative_read_patient_access = user_accesses.filter(Role.is_read_patient_role_nominative("role"))
        pseudo_read_patient_access = user_accesses.filter(Role.is_read_patient_role_pseudo("role"))

        # Get all distinct perimeter from accesses:
        all_nominative_perimeters = list(set([access.perimeter for access in nominative_read_patient_access]))
        all_pseudo_perimeters = list(set([access.perimeter for access in pseudo_read_patient_access]))

        top_nominative_accesses = list(set(get_top_accesses_nominative(nominative_read_patient_access,
                                                                       all_nominative_perimeters)))

        top_pseudo_accesses = list(set(get_top_accesses_pseudo(pseudo_read_patient_access,
                                                               all_nominative_perimeters, all_pseudo_perimeters)))

        # Apply Distinct to list
        top_hierarchy_accesses = list(set(top_nominative_accesses + top_pseudo_accesses))
        return Response(AccessSerializer(top_hierarchy_accesses, many=True).data)

    @swagger_auto_schema(
        manual_parameters=list(map(
            lambda x: openapi.Parameter(
                name=x[0], in_=openapi.IN_QUERY, description=x[1], type=x[2],
                pattern=x[3] if len(x) == 4 else None
            ), [
                [
                    "ordering",
                    "'field' or '-field' in care_site_name, "
                    "care_site_type_source_value, care_site_source_value, ",
                    openapi.TYPE_STRING
                ],
                [
                    "search",
                    "Will search in multiple fields (care_site_name, "
                    "care_site_type_source_value, care_site_source_value)",
                    openapi.TYPE_STRING
                ],
                [
                    "treefy",
                    "If true, returns a tree-organised json, else, "
                    "returns a list", openapi.TYPE_BOOLEAN
                ],
            ])))
    def list(self, request, *args, **kwargs):
        treefy = request.GET.get("treefy", None)
        if str(treefy).lower() == 'true':
            return self.treefied(request, *args, **kwargs)
        return super(PerimeterViewSet, self).list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Test",
        responses={
            '201': openapi.Response("Perimeters found",
                                    YasgTreefiedPerimeterSerializer),
            '401': openapi.Response("Not authenticated")
        }
    )
    @action(detail=False, methods=['get'], url_path="treefied")
    def treefied(self, request, *args, **kwargs):
        # in that case, for each perimeter filtered, we want to show the
        # branch of the whole perimeter tree that leads to it
        q = self.filter_queryset(self.get_queryset())
        if not q.count():
            return Response([])

        if q.count() != self.get_queryset().count():
            q = (q | get_all_perimeters_parents_queryset(q)).distinct()
            res = q.filter(~Q(parent__id__in=q.values_list("id", flat=True))) \
                .distinct()
        else:
            res = q.filter(parent__isnull=True)

        prefetch = Perimeter.children_prefetch(q)
        for _ in range(2, len(PERIMETERS_TYPES)):
            prefetch = Perimeter.children_prefetch(
                q.prefetch_related(prefetch))

        res = res.prefetch_related(prefetch)
        return Response(TreefiedPerimeterSerializer(res, many=True).data)


class NestedPerimeterViewSet(SwaggerSimpleNestedViewSetMixin, PerimeterViewSet):
    @swagger_auto_schema(auto_schema=None)
    def get_manageable(self, request, *args, **kwargs):
        return super(NestedPerimeterViewSet, self).get_manageable(
            request, *args, **kwargs)

    @swagger_auto_schema(auto_schema=None)
    def treefied(self, request, *args, **kwargs):
        return super(NestedPerimeterViewSet, self).treefied(
            request, *args, **kwargs)
