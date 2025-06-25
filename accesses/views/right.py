from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response

from accesses.models import Right
from accesses.serializers import RightSerializer
from accesses.services.rights import rights_service
from accesses.views import BaseViewSet
from admin_cohort.tools.cache import cache_response
from admin_cohort.permissions import IsAuthenticated
from admin_cohort.tools.negative_limit_paginator import NegativeLimitOffsetPagination


class RightsViewSet(BaseViewSet):
    queryset = Right.objects.filter(delete_datetime__isnull=True).all()
    serializer_class = RightSerializer
    lookup_field = "id"
    permission_classes = [IsAuthenticated]
    pagination_class = NegativeLimitOffsetPagination
    http_method_names = ["get"]
    filterset_fields = ["name",
                        "label",
                        "is_global",
                        "allow_edit_accesses_on_same_level",
                        "allow_edit_accesses_on_inf_levels"]
    swagger_tags = ["Rights"]

    @extend_schema(responses={status.HTTP_200_OK: RightSerializer(many=True)})
    @cache_response()
    def list(self, request, *args, **kwargs):
        return Response(data=rights_service.list_rights(), status=status.HTTP_200_OK)
