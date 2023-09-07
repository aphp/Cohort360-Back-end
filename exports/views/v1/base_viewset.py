from rest_framework import viewsets

from admin_cohort.tools.negative_limit_paginator import NegativeLimitOffsetPagination


class ExportsBaseViewSet(viewsets.ModelViewSet):
    lookup_field = "uuid"
    http_method_names = ["get", "post", "patch", "delete"]
    pagination_class = NegativeLimitOffsetPagination
