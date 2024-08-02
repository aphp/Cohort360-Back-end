from django.db import IntegrityError
from django_filters import OrderingFilter
from django_filters import rest_framework as filters
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from accesses.models import Role
from accesses.permissions import RolesPermission
from accesses.serializers import RoleSerializer, UsersInRoleSerializer
from accesses.services.roles import roles_service
from admin_cohort.tools.cache import cache_response
from admin_cohort.permissions import IsAuthenticated, UsersPermission
from admin_cohort.views import BaseViewSet
from admin_cohort.tools.request_log_mixin import RequestLogMixin


class RoleFilter(filters.FilterSet):
    name = filters.CharFilter(lookup_expr="icontains")
    ordering = OrderingFilter(fields=('name',))

    class Meta:
        model = Role
        fields = "__all__"


USERS_ORDERING_FIELDS = ["lastname", "firstname", "perimeter", "start_datetime", "end_datetime"]


class RoleViewSet(RequestLogMixin, BaseViewSet):
    queryset = Role.objects.filter(delete_datetime__isnull=True).all()
    serializer_class = RoleSerializer
    lookup_field = "id"
    http_method_names = ['get', 'post', 'patch', 'delete']
    logging_methods = ['POST', 'PATCH', 'DELETE']
    swagger_tags = ['Accesses - roles']
    filterset_class = RoleFilter
    permission_classes = [IsAuthenticated, RolesPermission]

    @cache_response()
    def list(self, request, *args, **kwargs):
        return super(RoleViewSet, self).list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        try:
            roles_service.check_role_has_inconsistent_rights(data=request.data.copy())
        except IntegrityError as e:
            return Response(data={"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return super(RoleViewSet, self).create(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        try:
            roles_service.check_role_has_inconsistent_rights(data=request.data.copy())
        except IntegrityError as e:
            return Response(data={"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return super(RoleViewSet, self).partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        role = self.get_object()
        if role.right_full_admin:
            return Response(data={"error": "Cannot delete the Full Admin role"}, status=status.HTTP_403_FORBIDDEN)
        if role.accesses.all().exists():
            return Response(data={"error": "This role is attached to existing accesses"}, status=status.HTTP_403_FORBIDDEN)
        self.perform_destroy(role)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(method='get',
                         operation_summary="Get the list of users who have that role",
                         manual_parameters=[openapi.Parameter(name="order", in_=openapi.IN_QUERY, type=openapi.TYPE_STRING,
                                                              description=f"Ordering of the results (prepend with '-' to reverse order)."
                                                                          f"Ordering fields are {','.join(USERS_ORDERING_FIELDS)}"),
                                            openapi.Parameter(name="filter_by_name", description="Filter by name",
                                                              in_=openapi.IN_QUERY, type=openapi.TYPE_STRING)],
                         responses={200: openapi.Response('Users having this role', UsersInRoleSerializer),
                                    204: openapi.Response('No content')})
    @action(url_path="users", detail=True, methods=['get'], permission_classes=permission_classes+[UsersPermission])
    def users_within_role(self, request, *args, **kwargs):
        role = self.get_object()
        users_perimeters = []
        valid_accesses = [a for a in role.accesses.all() if a.is_valid]
        for access in valid_accesses:
            user = access.profile.user
            users_perimeters.append({"username": user.username,
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
                                normalized_filter in user_perimeter["username"] or
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
    def get_assignable_roles(self, request, *args, **kwargs):
        perimeter_id = request.GET.get("perimeter_id")
        if not perimeter_id:
            return Response(data={"error": "Missing parameter: `perimeter_id`"}, status=status.HTTP_400_BAD_REQUEST)
        assignable_roles_ids = roles_service.get_assignable_roles_ids(user=request.user,
                                                                      perimeter_id=perimeter_id,
                                                                      queryset=self.get_queryset())
        assignable_roles = self.get_queryset().filter(id__in=assignable_roles_ids)
        return Response(data=RoleSerializer(assignable_roles, many=True).data,
                        status=status.HTTP_200_OK)
