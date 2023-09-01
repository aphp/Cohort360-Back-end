from django.http import QueryDict
from django_filters import rest_framework as filters, OrderingFilter
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_extensions.mixins import NestedViewSetMixin

from admin_cohort.tools.cache import cache_response
from admin_cohort.tools.negative_limit_paginator import NegativeLimitOffsetPagination
from cohort.models import RequestQuerySnapshot
from cohort.permissions import IsOwner
from cohort.serializers import RequestQuerySnapshotSerializer
from cohort.services.request_query_snapshot import rqs_service
from cohort.views.shared import UserObjectsRestrictedViewSet


class RequestQuerySnapshotFilter(filters.FilterSet):
    ordering = OrderingFilter(fields=('-created_at', 'modified_at'))

    class Meta:
        model = RequestQuerySnapshot
        fields = ('uuid', 'request', 'is_active_branch', 'shared_by',
                  'previous_snapshot', 'request', 'request__parent_folder')


class RequestQuerySnapshotViewSet(NestedViewSetMixin, UserObjectsRestrictedViewSet):
    queryset = RequestQuerySnapshot.objects.all()
    serializer_class = RequestQuerySnapshotSerializer
    http_method_names = ['get', 'post']
    lookup_field = "uuid"
    swagger_tags = ['Cohort - request-query-snapshots']
    pagination_class = NegativeLimitOffsetPagination
    filterset_class = RequestQuerySnapshotFilter
    search_fields = ('$serialized_query',)

    @cache_response()
    def list(self, request, *args, **kwargs):
        return super(RequestQuerySnapshotViewSet, self).list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        return super(RequestQuerySnapshotViewSet, self).retrieve(request, *args, **kwargs)

    @swagger_auto_schema(method='post',
                         operation_summary="Share RequestQuerySnapshot with a User by creating a new Request in its Shared Folder.\n"
                                           "'recipients' are strings joined with ','. 'name' is optional",
                         request_body=openapi.Schema(type=openapi.TYPE_OBJECT,
                                                     properties={"recipients": openapi.Schema(type=openapi.TYPE_STRING),
                                                                 "name": openapi.Schema(type=openapi.TYPE_STRING),
                                                                 "notify_by_email": openapi.Schema(
                                                                     type=openapi.TYPE_BOOLEAN, default=False)
                                                                 }),
                         responses={'201': openapi.Response("New requests created for recipients",
                                                            RequestQuerySnapshotSerializer(many=True)),
                                    '400': openapi.Response("One or more recipient's not found"),
                                    '404': openapi.Response("RequestQuerySnapshot not found (possibly not owned)")})
    @action(detail=True, methods=['post'], permission_classes=(IsOwner,), url_path="share")
    def share(self, request, *args, **kwargs):
        shared_rqs = rqs_service.share_snapshot(rqs=self.get_object(),
                                                request_name=request.data.get('name'),
                                                recipients_ids=request.data.get('recipients'),
                                                notify_by_email=request.data.get('notify_by_email', False))
        return Response(data=RequestQuerySnapshotSerializer(shared_rqs, many=True).data,
                        status=status.HTTP_201_CREATED)


class NestedRqsViewSet(RequestQuerySnapshotViewSet):

    def create(self, request, *args, **kwargs):
        if type(request.data) == QueryDict:
            request.data._mutable = True

        if 'request_id' in kwargs:
            request.data["request"] = kwargs['request_id']
        if 'previous_snapshot' in kwargs:
            request.data["previous_snapshot"] = kwargs['previous_snapshot']

        return super(NestedRqsViewSet, self).create(request, *args, **kwargs)
