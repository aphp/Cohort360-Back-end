from django.core.cache import cache
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from admin_cohort.permissions import CachePermission


class CacheViewSet(APIView):
    http_method_names = ["get", "delete"]
    permission_classes = (CachePermission,)

    @swagger_auto_schema(operation_description="List cached responses",
                         manual_parameters=[openapi.Parameter(name="username", in_=openapi.IN_QUERY,
                                                              description="Get cached responses for a specific user",
                                                              type=openapi.TYPE_STRING),
                                            openapi.Parameter(name="keys_only", in_=openapi.IN_QUERY,
                                                              description="Retrieve cache keys only",
                                                              type=openapi.TYPE_BOOLEAN)])
    def get(self, request, *args, **kwargs):
        search_pattern = "*"
        username = request.query_params.get('username')
        if username:
            search_pattern = f"*{username}*"
        keys = sorted(cache.keys(search_pattern))
        data = dict((k, cache.get(k)) for k in keys)
        keys_only = request.query_params.get('keys_only')
        if keys_only:
            return Response(data=keys, status=status.HTTP_200_OK)
        return Response(data=data, status=status.HTTP_200_OK)

    @swagger_auto_schema(operation_description="Delete cache records. Pass no parameter to clear the cache for all users",
                         manual_parameters=[openapi.Parameter(name="username", in_=openapi.IN_QUERY,
                                                              description="Clear cache for the specified user",
                                                              type=openapi.TYPE_STRING)])
    def delete(self, request, *args, **kwargs):
        target_pattern = "*"
        username = request.query_params.get('username')
        if username:
            target_pattern = f"*{username}*"
        cache.delete_pattern(target_pattern)
        return Response(status=status.HTTP_204_NO_CONTENT)
