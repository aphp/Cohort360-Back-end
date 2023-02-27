from django.http import QueryDict
from django_filters import rest_framework as filters, OrderingFilter
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response
from rest_framework_extensions.mixins import NestedViewSetMixin

from admin_cohort.models import User
from cohort.models import RequestQuerySnapshot
from cohort.permissions import IsOwner
from cohort.serializers import RequestQuerySnapshotSerializer
from cohort.views.shared import UserObjectsRestrictedViewSet


class RQSFilter(filters.FilterSet):
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
    pagination_class = LimitOffsetPagination
    filterset_class = RQSFilter
    search_fields = ('$serialized_query',)

    def update(self, request, *args, **kwargs):
        return Response(data={"response": "RQS manual update not allowed"},
                        status=status.HTTP_403_FORBIDDEN)

    def partial_update(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    @action(detail=True, methods=['post'], permission_classes=(IsOwner,), url_path="save")
    def save(self, req, request_query_snapshot_uuid):
        try:
            rqs = RequestQuerySnapshot.objects.get(uuid=request_query_snapshot_uuid)
        except RequestQuerySnapshot.DoesNotExist:
            return Response(data={"response": "request_query_snapshot not found"},
                            status=status.HTTP_404_NOT_FOUND)
        rqs.save_snapshot()
        return Response(data={'response': "Query successful!"},
                        status=status.HTTP_200_OK)

    @swagger_auto_schema(method='post',
                         operation_summary="Share RequestQuerySnapshot with a User by creating a new Request in its Shared Folder.\n"
                                           "'recipients' are strings joined with ','. 'name' is optional",
                         request_body=openapi.Schema(type=openapi.TYPE_OBJECT,
                                                     properties={"recipients": openapi.Schema(type=openapi.TYPE_STRING),
                                                                 "name": openapi.Schema(type=openapi.TYPE_STRING)}),
                         responses={'201': openapi.Response("New requests created for recipients", RequestQuerySnapshotSerializer(many=True)),
                                    '400': openapi.Response("One or more recipient's not found"),
                                    '404': openapi.Response("RequestQuerySnapshot not found (possibly not owned)")})
    @action(detail=True, methods=['post'], permission_classes=(IsOwner,), url_path="share")
    def share(self, request, *args, **kwargs):
        recipients = request.data.get('recipients')
        if not recipients:
            raise ValidationError("'recipients' doit être fourni")

        recipients = recipients.split(",")
        name = request.data.get('name', None)

        users = User.objects.filter(pk__in=recipients)
        users_ids = [str(u.pk) for u in users]
        errors = [r for r in recipients if r not in users_ids]

        if errors:
            raise ValidationError(f"Les utilisateurs avec les IDs suivants n'ont pas été trouvés: {','.join(errors)}")

        rqs = self.get_object()
        shared_rqs = rqs.share(users, name)
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
