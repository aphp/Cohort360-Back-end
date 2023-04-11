import logging

from django_filters import rest_framework as filters, OrderingFilter
from rest_framework.pagination import LimitOffsetPagination
from rest_framework_extensions.mixins import NestedViewSetMixin

from cohort.models import DatedMeasure
from cohort.serializers import DatedMeasureSerializer
from cohort.views.shared import UserObjectsRestrictedViewSet

_logger = logging.getLogger('django.request')


class DMFilter(filters.FilterSet):
    request_id = filters.CharFilter(field_name='request_query_snapshot__request__pk')
    ordering = OrderingFilter(fields=("-created_at", "modified_at", "result_size"))

    class Meta:
        model = DatedMeasure
        fields = ('uuid',
                  'mode',
                  'request_id',
                  'count_task_id',
                  'request_query_snapshot',
                  'request_query_snapshot__request')


class DatedMeasureViewSet(NestedViewSetMixin, UserObjectsRestrictedViewSet):
    queryset = DatedMeasure.objects.all()
    serializer_class = DatedMeasureSerializer
    http_method_names = ['get', 'post']
    lookup_field = "uuid"
    swagger_tags = ['Cohort - dated-measures']
    filterset_class = DMFilter
    pagination_class = LimitOffsetPagination
