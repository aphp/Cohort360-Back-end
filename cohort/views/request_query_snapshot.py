from django.http import QueryDict
from django_filters import rest_framework as filters, OrderingFilter
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_extensions.mixins import NestedViewSetMixin

from admin_cohort.tools.negative_limit_paginator import NegativeLimitOffsetPagination
from cohort.models import RequestQuerySnapshot
from cohort.permissions import IsOwnerPermission
from cohort.serializers import RequestQuerySnapshotSerializer, RequestQuerySnapshotCreateSerializer, RequestQuerySnapshotShareSerializer
from cohort.services.request_query_snapshot import rqs_service
from cohort.views.shared import UserObjectsRestrictedViewSet


class RequestQuerySnapshotFilter(filters.FilterSet):
    ordering = OrderingFilter(fields=('-created_at', 'modified_at'))

    class Meta:
        model = RequestQuerySnapshot
        fields = ('uuid', 'request', 'shared_by',
                  'previous_snapshot', 'request', 'request__parent_folder')


class RequestQuerySnapshotViewSet(NestedViewSetMixin, UserObjectsRestrictedViewSet):
    queryset = RequestQuerySnapshot.objects.exclude(cohort_results__is_subset=True)
    serializer_class = RequestQuerySnapshotSerializer
    http_method_names = ['get', 'post']
    lookup_field = "uuid"
    swagger_tags = ['Request Query Snapshots']
    pagination_class = NegativeLimitOffsetPagination
    filterset_class = RequestQuerySnapshotFilter
    search_fields = ('$serialized_query',)

    @extend_schema(tags=swagger_tags,
                   responses={status.HTTP_200_OK: RequestQuerySnapshotSerializer})
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(tags=swagger_tags,
                   responses={status.HTTP_200_OK: RequestQuerySnapshotSerializer})
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(tags=swagger_tags,
                   request=RequestQuerySnapshotCreateSerializer,
                   responses={status.HTTP_201_CREATED: RequestQuerySnapshotSerializer})
    def create(self, request, *args, **kwargs):
        try:
            rqs_service.process_creation_data(data=request.data)
        except ValueError as ve:
            return Response(data=f"{ve}", status=status.HTTP_400_BAD_REQUEST)
        return super().create(request, *args, **kwargs)

    @extend_schema(tags=swagger_tags,
                   request=RequestQuerySnapshotShareSerializer,
                   responses={status.HTTP_201_CREATED: RequestQuerySnapshotSerializer})
    @action(detail=True, methods=['post'], permission_classes=(IsOwnerPermission,), url_path="share")
    def share(self, request, *args, **kwargs):
        try:
            shared_rqs = rqs_service.share_snapshot(snapshot=self.get_object(),
                                                    request_name=request.data.get('name'),
                                                    recipients_ids=request.data.get('recipients'),
                                                    notify_by_email=request.data.get('notify_by_email', False))
        except ValueError as ve:
            return Response(data=f"{ve}", status=status.HTTP_400_BAD_REQUEST)
        return Response(data=RequestQuerySnapshotSerializer(shared_rqs, many=True).data,
                        status=status.HTTP_201_CREATED)


class NestedRqsViewSet(RequestQuerySnapshotViewSet):

    @extend_schema(tags=RequestQuerySnapshotViewSet.swagger_tags,
                   request=RequestQuerySnapshotCreateSerializer,
                   responses={status.HTTP_201_CREATED: RequestQuerySnapshotSerializer})
    def create(self, request, *args, **kwargs):
        if type(request.data) is QueryDict:
            request.data._mutable = True

        if 'request_id' in kwargs:
            request.data["request"] = kwargs['request_id']
        if 'previous_snapshot' in kwargs:
            request.data["previous_snapshot"] = kwargs['previous_snapshot']

        return super().create(request, *args, **kwargs)
