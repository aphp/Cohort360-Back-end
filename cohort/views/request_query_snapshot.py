from django.http import QueryDict
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_extensions.mixins import NestedViewSetMixin

from cohort.models import RequestQuerySnapshot
from cohort.serializers import RQSSerializer, RQSCreateSerializer, RQSShareSerializer
from cohort.services.request_query_snapshot import rqs_service
from cohort.views.shared import UserObjectsRestrictedViewSet


@extend_schema_view(
    list=extend_schema(exclude=True),
    retrieve=extend_schema(responses={status.HTTP_200_OK: RQSSerializer}),
)
class RequestQuerySnapshotViewSet(NestedViewSetMixin, UserObjectsRestrictedViewSet):
    queryset = RequestQuerySnapshot.objects.exclude(cohort_results__is_subset=True)
    serializer_class = RQSSerializer
    http_method_names = ['get', 'post']
    swagger_tags = ['Request Query Snapshots']

    @extend_schema(request=RQSCreateSerializer, responses={status.HTTP_201_CREATED: RQSSerializer})
    def create(self, request, *args, **kwargs):
        try:
            rqs_service.process_creation_data(data=request.data)
        except ValueError as ve:
            return Response(data=f"{ve}", status=status.HTTP_400_BAD_REQUEST)
        return super().create(request, *args, **kwargs)

    @extend_schema(request=RQSShareSerializer, responses={status.HTTP_201_CREATED: None})
    @action(detail=True, methods=['post'], url_path="share")
    def share(self, request, *args, **kwargs):
        try:
            rqs_service.share_snapshot(snapshot=self.get_object(),
                                       request_name=request.data.get('name'),
                                       recipients_ids=request.data.get('recipients'),
                                       notify_by_email=request.data.get('notify_by_email', False))
        except ValueError as ve:
            return Response(data=f"{ve}", status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_201_CREATED)


class NestedRqsViewSet(RequestQuerySnapshotViewSet):

    def create(self, request, *args, **kwargs):
        if type(request.data) is QueryDict:
            request.data._mutable = True

        if 'request_id' in kwargs:
            request.data["request"] = kwargs['request_id']
        if 'previous_snapshot' in kwargs:
            request.data["previous_snapshot"] = kwargs['previous_snapshot']

        return super().create(request, *args, **kwargs)
