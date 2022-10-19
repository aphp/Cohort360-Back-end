import django_filters
from django.db.models import Q

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.decorators import action
from rest_framework.response import Response

from rest_framework_extensions.mixins import NestedViewSetMixin

from ..models import Role, Perimeter, get_user_valid_manual_accesses_queryset, \
    get_all_perimeters_parents_queryset
from ..serializers import PerimeterSerializer, \
    TreefiedPerimeterSerializer, YasgTreefiedPerimeterSerializer
from admin_cohort.permissions import IsAuthenticatedReadOnly
from admin_cohort.settings import PERIMETERS_TYPES
from admin_cohort.tools import join_qs
from admin_cohort.views import BaseViewset, YarnReadOnlyViewsetMixin,\
    SwaggerSimpleNestedViewSetMixin


class PerimeterFilter(django_filters.FilterSet):
    care_site_name = django_filters.CharFilter(field_name='name')
    care_site_type_source_value = django_filters.CharFilter(field_name='type_source_value')
    care_site_source_value = django_filters.CharFilter(field_name='source_value')
    care_site_id = django_filters.CharFilter(field_name='id')
    name = django_filters.CharFilter(lookup_expr='icontains')
    source_value = django_filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = Perimeter
        fields = (
            "care_site_name",
            "care_site_type_source_value",
            "care_site_source_value",
            "care_site_id",
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
    # todo : check if works with param name
    ordering_fields = [('care_site_name', 'name'),
                       ('care_site_type_source_value', 'type_source_value'),
                       ('care_site_source_value', 'source_value')]
    search_fields = ["name",
                     "type_source_value",
                     "source_value"]

    @swagger_auto_schema(
        method='get',
        operation_summary="Get the perimeters on which the user has at least "
                          "one role that allows to give accesses.",
        manual_parameters=list(map(
            lambda x: openapi.Parameter(
                name=x[0], in_=openapi.IN_QUERY, description=x[1], type=x[2],
                pattern=x[3] if len(x) == 4 else None
            ), [
                [
                    "search",
                    "Will search in multiple fields (care_site_name, "
                    "care_site_type_source_value, care_site_source_value)",
                    openapi.TYPE_STRING
                ],
                [
                    "nb_levels",
                    "Indicates the limit of children layers to reply.",
                    openapi.TYPE_INTEGER
                ],
            ]
        )),
        responses={
            '201': openapi.Response("manageable perimeters found",
                                    YasgTreefiedPerimeterSerializer()
                                    ),
        }
    )
    @action(detail=False, methods=['get'], url_path="manageable")
    def get_manageable(self, request, *args, **kwargs):
        user_accesses = get_user_valid_manual_accesses_queryset(
            self.request.user)

        if user_accesses.filter(Role.edit_on_any_level_query("role")).count():
            # in that case, perims to retun is all perimeters
            # and queryset result will only contain the top perimeters
            perims = self.get_queryset()
            q = Perimeter.objects.filter(parent__isnull=True)
        else:
            # in that case, perims to returns depends on roles
            # and queryset result will only contain the top of those perimeters
            acc_ids = user_accesses.values_list("id", flat=True)
            perims = Perimeter.objects.filter(join_qs(
                [Role.edit_on_lower_levels_query(
                    f"{i * 'parent__'}accesses__role",
                    {f'{i * "parent__"}accesses__id__in': acc_ids}
                ) for i in range(1, len(PERIMETERS_TYPES))
                ] + [Role.edit_on_same_level_query(
                    "accesses__role",
                    {'accesses__id__in': acc_ids}
                )]
            )).distinct()

            q = perims.filter(~Q(
                parent__id__in=perims.values_list("id", flat=True)))

        prefetch = Perimeter.children_prefetch(perims)
        nb_levels = int(request.GET.get('nb_levels', len(PERIMETERS_TYPES)))
        for _ in range(2, nb_levels):
            prefetch = Perimeter.children_prefetch(perims
                                                   .prefetch_related(prefetch))

        q = q.prefetch_related(prefetch)
        return Response(TreefiedPerimeterSerializer(q, many=True).data)

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
            res = q.filter(~Q(parent__id__in=q.values_list("id", flat=True)))\
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
