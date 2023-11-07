from django_filters import OrderingFilter
from django_filters import rest_framework as filters
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from accesses.models import Role, Perimeter
from accesses.permissions import RolesPermission
from accesses.serializers import RoleSerializer, UsersInRoleSerializer
from accesses.tools import do_user_accesses_allow_to_manage_role, check_existing_role, get_assignable_roles
from admin_cohort.tools.cache import cache_response
from admin_cohort.permissions import IsAuthenticated, UsersPermission
from admin_cohort.tools.negative_limit_paginator import NegativeLimitOffsetPagination
from admin_cohort.views import BaseViewset, CustomLoggingMixin


class RoleFilter(filters.FilterSet):
    name = filters.CharFilter(lookup_expr="icontains")
    ordering = OrderingFilter(fields=('name',))

    class Meta:
        model = Role
        fields = "__all__"


USERS_ORDERING_FIELDS = ["lastname", "firstname", "perimeter", "start_datetime", "end_datetime"]


class RoleViewSet(CustomLoggingMixin, BaseViewset):
    serializer_class = RoleSerializer
    queryset = Role.objects.filter(delete_datetime__isnull=True).all()
    lookup_field = "id"
    http_method_names = ['post', 'patch', 'delete']
    logging_methods = ['POST', 'PATCH', 'DELETE']
    swagger_tags = ['Accesses - roles']
    filterset_class = RoleFilter
    permission_classes = [IsAuthenticated, RolesPermission]
    pagination_class = NegativeLimitOffsetPagination

    @cache_response()
    def list(self, request, *args, **kwargs):
        return super(RoleViewSet, self).list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        role = check_existing_role(data=request.data)
        if role:
            return Response(data=f"Un rôle avec les mêmes droits est déjà configuré: <{role.name}>",
                            status=status.HTTP_400_BAD_REQUEST)
        return super(RoleViewSet, self).create(request, *args, **kwargs)

    @swagger_auto_schema(method='get',
                         operation_summary="Get the list of users that have that role",
                         manual_parameters=[openapi.Parameter(name="order", in_=openapi.IN_QUERY,
                                                              description=f"Ordering of the results (prepend with '-' "
                                                                          f"to reverse order), ordering"
                                                                          f" fields are "
                                                                          f"{','.join(USERS_ORDERING_FIELDS)}",
                                                              type=openapi.TYPE_STRING),
                                            openapi.Parameter(name="filter_by_name", in_=openapi.IN_QUERY,
                                                              description="Filter by name", type=openapi.TYPE_STRING)],
                         responses={
                             200: openapi.Response('All valid accesses or ones to expire soon', UsersInRoleSerializer),
                             204: openapi.Response('No content')})
    @action(url_path="users", detail=True, methods=['get'], permission_classes=permission_classes+[UsersPermission])
    def users_within_role(self, request, *args, **kwargs):
        role = self.get_object()
        users_perimeters = []
        valid_accesses = [a for a in role.accesses.all() if a.is_valid]
        for access in valid_accesses:
            user = access.profile.user
            users_perimeters.append({"provider_username": user.provider_username,
                                     "firstname": user.firstname,
                                     "lastname": user.lastname,
                                     "email": user.email,
                                     "perimeter": access.perimeter.name,
                                     "start_datetime": access.start_datetime,
                                     "end_datetime": access.end_datetime,
                                     })

        # filtering
        filter_by_name = request.query_params.get('filter_by_name')
        if filter_by_name:
            normalized_filter = filter_by_name.lower()
            users_perimeters = [user_perimeter for user_perimeter in users_perimeters if
                                normalized_filter in user_perimeter["provider_username"] or
                                normalized_filter in user_perimeter['firstname'].lower() or
                                normalized_filter in user_perimeter["lastname"].lower()]

        # sorting
        order = request.query_params.get("order", "lastname")
        reverse_order = False
        if order.startswith('-'):
            reverse_order = True
            order = order[1:]
        users_perimeters = sorted(users_perimeters, key=lambda x: x.get(order, ''), reverse=reverse_order)

        if users_perimeters:
            page = self.paginate_queryset(users_perimeters)
            serializer = UsersInRoleSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(method='get',
                         operation_summary="Get roles that the user can assign to a user on the provided perimeter",
                         manual_parameters=[openapi.Parameter(name="perimeter_id", in_=openapi.IN_QUERY,
                                                              description="Required", type=openapi.TYPE_INTEGER)])
    @action(url_path="assignable", detail=False, methods=['get'])
    @cache_response()
    def assignable(self, request, *args, **kwargs):
        perimeter_id = request.GET.get("perimeter_id")    # todo: [front] remove care_site_id
        if not perimeter_id:
            return Response(data="Missing parameter: `perimeter_id`", status=status.HTTP_400_BAD_REQUEST)
        assignable_roles = get_assignable_roles(user=request.user, perimeter_id=perimeter_id)
        page = self.paginate_queryset(assignable_roles)
        if page:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        return Response(status=status.HTTP_204_NO_CONTENT)
