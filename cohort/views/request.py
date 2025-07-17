from django.db.models.expressions import Subquery, OuterRef
from django.db.models.query import Prefetch
from django.http import QueryDict
from django_filters import rest_framework as filters, OrderingFilter
from drf_spectacular.utils import extend_schema_view, extend_schema
from rest_framework import status
from rest_framework_extensions.mixins import NestedViewSetMixin

from admin_cohort.tools.cache import cache_response
from cohort.models import Request, RequestQuerySnapshot as RQS
from cohort.serializers import RequestSerializer, RequestCreateSerializer, RequestPatchSerializer
from cohort.views.shared import UserObjectsRestrictedViewSet


class RequestFilter(filters.FilterSet):
    min_updated_at = filters.IsoDateTimeFilter(field_name='updated_at', lookup_expr="gte")
    max_updated_at = filters.IsoDateTimeFilter(field_name='updated_at', lookup_expr="lte")

    ordering = OrderingFilter(fields=('name',
                                      'updated_at',
                                      ('parent_folder__name', 'parent_folder')))

    class Meta:
        model = Request
        fields = ('favorite',
                  'shared_by',
                  'parent_folder',
                  'min_updated_at',
                  'max_updated_at',)


@extend_schema_view(
    list=extend_schema(responses={status.HTTP_200_OK: RequestSerializer(many=True)}),
    retrieve=extend_schema(responses={status.HTTP_200_OK: RequestSerializer}),
    create=extend_schema(request=RequestCreateSerializer,
                         responses={status.HTTP_201_CREATED: RequestSerializer}),
    partial_update=extend_schema(request=RequestPatchSerializer,
                                 responses={status.HTTP_200_OK: RequestSerializer}),
    destroy=extend_schema(responses={status.HTTP_204_NO_CONTENT: None})
)
class RequestViewSet(NestedViewSetMixin, UserObjectsRestrictedViewSet):
    query_snapshots_subquery = RQS.objects.filter(request_id=OuterRef('uuid')) \
                                          .order_by('-created_at') \
                                          .values('created_at')[:1]
    queryset = Request.objects.prefetch_related(Prefetch(lookup='query_snapshots',
                                                         queryset=RQS.objects.prefetch_related('cohort_results'))) \
                              .annotate(updated_at=Subquery(query_snapshots_subquery.values('created_at')))
    serializer_class = RequestSerializer
    http_method_names = ["get", "post", "patch", "delete"]
    filterset_class = RequestFilter
    search_fields = ("$name", "$description",)
    swagger_tags = ["Requests"]

    @cache_response()
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class NestedRequestViewSet(RequestViewSet):

    def create(self, request, *args, **kwargs):
        if type(request.data) is QueryDict:
            request.data._mutable = True
        if 'parent_folder' in kwargs:
            request.data["parent_folder"] = kwargs['parent_folder']
        return super().create(request, *args, **kwargs)
