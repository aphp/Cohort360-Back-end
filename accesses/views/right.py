from rest_framework import status
from rest_framework.response import Response

from accesses.models import Right
from accesses.serializers import RightSerializer
from accesses.services.rights import rights_service
from admin_cohort.tools.cache import cache_response
from admin_cohort.permissions import IsAuthenticated
from admin_cohort.tools.negative_limit_paginator import NegativeLimitOffsetPagination
from admin_cohort.views import BaseViewSet


class RightsViewSet(BaseViewSet):
    queryset = Right.objects.filter(delete_datetime__isnull=True).all()
    serializer_class = RightSerializer
    lookup_field = "id"
    http_method_names = ['get']
    swagger_tags = ['Accesses - rights']
    permission_classes = [IsAuthenticated]
    pagination_class = NegativeLimitOffsetPagination

    @cache_response()
    def list(self, request, *args, **kwargs):
        return Response(data=rights_service.list_rights(), status=status.HTTP_200_OK)
