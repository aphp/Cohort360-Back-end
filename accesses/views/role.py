from django_filters import OrderingFilter
from django_filters import rest_framework as filters
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AND
from rest_framework.response import Response

from admin_cohort.permissions import IsAuthenticated
from admin_cohort.views import BaseViewset, CustomLoggingMixin
from ..models import Role, get_assignable_roles_on_perimeter, Perimeter
from ..permissions import RolePermissions
from ..serializers import RoleSerializer, UsersInRoleSerializer


class RoleFilter(filters.FilterSet):
    name = filters.CharFilter(lookup_expr="icontains")
    ordering = OrderingFilter(fields=('name',))

    class Meta:
        model = Role
        fields = "__all__"


class RoleViewSet(CustomLoggingMixin, BaseViewset):
    serializer_class = RoleSerializer
    queryset = Role.objects.filter(delete_datetime__isnull=True).all()
    lookup_field = "id"
    logging_methods = ['POST', 'PUT', 'PATCH', 'DELETE']
    swagger_tags = ['Accesses - roles']
    filterset_class = RoleFilter

    def get_permissions(self):
        return [AND(IsAuthenticated(), RolePermissions())]

    @action(url_path="users", detail=True, methods=['get'], permission_classes=(IsAuthenticated,))
    def users_within_role(self, request, *args, **kwargs):
        role = self.get_object()
        users_perimeters = []
        valid_accesses = [a for a in role.accesses.all() if a.is_valid]
        for a in valid_accesses:
            user = a.profile.user
            users_perimeters.append({"provider_username": user.provider_username,
                                     "firstname": user.firstname,
                                     "lastname": user.lastname,
                                     "email": user.email,
                                     "perimeter": a.perimeter.name
                                     })
        if users_perimeters:
            data = UsersInRoleSerializer(users_perimeters, many=True).data
            return Response(data=data, status=status.HTTP_200_OK)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(method='get',
                         operation_summary="Get roles that the user can assign to a user on the perimeter provided.",
                         manual_parameters=[openapi.Parameter(name="care_site_id", in_=openapi.IN_QUERY,
                                                              description="(to deprecate -> perimeter_id) Required",
                                                              type=openapi.TYPE_INTEGER),
                                            openapi.Parameter(name="perimeter_id", in_=openapi.IN_QUERY,
                                                              description="Required", type=openapi.TYPE_INTEGER)])
    @action(url_path="assignable", detail=False, methods=['get'], permission_classes=(IsAuthenticated,))
    def assignable(self, request, *args, **kwargs):
        perim_id = self.request.GET.get("perimeter_id", self.request.GET.get("care_site_id"))
        if not perim_id:
            raise ValidationError("Missing parameter 'perimeter_id'.")
        perim = Perimeter.objects.filter(id=perim_id).first()
        if not perim:
            raise ValidationError(f"Perimeter with id {perim_id} not found.")

        roles = get_assignable_roles_on_perimeter(self.request.user, perim)
        q = Role.objects.filter(id__in=[r.id for r in roles])
        page = self.paginate_queryset(q)
        if page:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        return Response(status=status.HTTP_204_NO_CONTENT)
