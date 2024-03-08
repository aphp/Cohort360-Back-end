from accesses.models import RightCategory
from accesses.serializers import RightCategorySerializer
from admin_cohort.tools.cache import cache_response
from admin_cohort.permissions import IsAuthenticated
from admin_cohort.tools.negative_limit_paginator import NegativeLimitOffsetPagination
from admin_cohort.views import BaseViewSet


class RightViewSet(BaseViewSet):
    queryset = RightCategory.objects.filter(delete_datetime__isnull=True).all()
    serializer_class = RightCategorySerializer
    lookup_field = "id"
    http_method_names = ['get']
    swagger_tags = ['Accesses - rights']
    permission_classes = [IsAuthenticated]
    pagination_class = NegativeLimitOffsetPagination

    @cache_response()
    def list(self, request, *args, **kwargs):
        return super(RightViewSet, self).list(request, *args, **kwargs)
