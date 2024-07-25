from django_filters import rest_framework as filters, OrderingFilter
from rest_framework import viewsets

from admin_cohort.tools.negative_limit_paginator import NegativeLimitOffsetPagination
from admin_cohort.types import JobStatus
from cohort.models import CohortResult
from cohort.permissions import IsOwnerPermission
from exports.serializers import AnnexeCohortResultSerializer


class CohortFilter(filters.FilterSet):
    ordering = OrderingFilter(fields=('name', 'created_at'))

    class Meta:
        model = CohortResult
        fields = ('owner_id',)


class CohortViewSet(viewsets.ModelViewSet):
    lookup_field = "uuid"
    http_method_names = ["get"]
    permission_classes = [IsOwnerPermission]
    serializer_class = AnnexeCohortResultSerializer
    queryset = CohortResult.objects.filter(request_job_status=JobStatus.finished,
                                           is_subset=False)
    swagger_tags = ['Exports - cohorts']
    filterset_class = CohortFilter
    pagination_class = NegativeLimitOffsetPagination
    search_fields = ('$name', '$description')

    def list(self, request, *args, **kwargs):
        return super(CohortViewSet, self).list(request, *args, **kwargs)
