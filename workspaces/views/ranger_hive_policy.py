from drf_yasg import openapi
from drf_yasg.openapi import Schema
from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from admin_cohort.permissions import IsAuthenticated
from admin_cohort.settings import RANGER_HIVE_POLICY_TYPES
from workspaces.models.ranger_hive_policy import RangerHivePolicy
from workspaces.permissions import AccountPermissions
from workspaces.serializers import RangerHivePolicySerializer


class RangerHivePolicyViewSet(viewsets.ModelViewSet):
    serializer_class = RangerHivePolicySerializer
    queryset = RangerHivePolicy.objects.all()
    lookup_field = "id"
    http_method_names = ["get"]
    permission_classes = [AccountPermissions]
    swagger_tags = ['Workspaces - ranger-hive-policies']

    def get_permissions(self):
        if self.action == 'get_types':
            return [IsAuthenticated()]
        return super(RangerHivePolicyViewSet, self).get_permissions()

    @swagger_auto_schema(methods=['get'], manual_parameters=[],
                         responses={status.HTTP_200_OK: openapi.Response(
                             description="Available types for Ranger Hive Policy",
                             schema=Schema(title='List of types', type=openapi.TYPE_ARRAY,
                                           items=Schema(type=openapi.TYPE_STRING)))})
    @action(detail=False, methods=['get'], url_path="types")
    def get_types(self, request: Request):
        return Response(RANGER_HIVE_POLICY_TYPES, status=status.HTTP_200_OK)
