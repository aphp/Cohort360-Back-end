import logging

from django.db import transaction
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.response import Response
from rest_framework_extensions.mixins import NestedViewSetMixin

from cohort.models import DatedMeasure
from cohort.serializers import DatedMeasureSerializer, DatedMeasureCreateSerializer, DatedMeasurePatchSerializer
from cohort.services.dated_measure import dm_service
from cohort.services.request_refresh_schedule import requests_refresher_service
from cohort.services.utils import await_celery_task, get_authorization_header
from cohort.views.shared import UserObjectsRestrictedViewSet

_logger = logging.getLogger('info')
_logger_err = logging.getLogger('django.request')


@extend_schema_view(
    list=extend_schema(exclude=True),
    create=extend_schema(request=DatedMeasureCreateSerializer,
                         responses={status.HTTP_201_CREATED: DatedMeasureSerializer}),
    partial_update=extend_schema(request=DatedMeasurePatchSerializer,
                                 responses={status.HTTP_200_OK: DatedMeasureSerializer})
)
class DatedMeasureViewSet(NestedViewSetMixin, UserObjectsRestrictedViewSet):
    queryset = DatedMeasure.objects.all()
    serializer_class = DatedMeasureSerializer
    http_method_names = ['get', 'post', 'patch']
    swagger_tags = ['Dated Measures']

    def get_permissions(self):
        special_permissions = dm_service.get_special_permissions(self.request)
        if special_permissions:
            return special_permissions
        return super().get_permissions()

    def get_queryset(self):
        if dm_service.allow_use_full_queryset(request=self.request):
            return self.queryset
        return super().get_queryset()

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        auth_headers = get_authorization_header(request)
        stage_details = request.data.get("stageDetails", None)
        transaction.on_commit(lambda: dm_service.handle_count(dm=response.data.serializer.instance,
                                                              auth_headers=auth_headers,
                                                              stage_details=stage_details))
        return response

    @await_celery_task
    def partial_update(self, request, *args, **kwargs):
        dm = self.get_object()
        try:
            dm_service.handle_patch_dated_measure(dm=dm, data=request.data)
        except ValueError as ve:
            dm_service.mark_dm_as_failed(dm=dm, reason=str(ve))
            response = Response(data=str(ve), status=status.HTTP_400_BAD_REQUEST)
        else:
            response = super().partial_update(request, *args, **kwargs)
        dm_service.ws_send_to_client(dm=dm)
        requests_refresher_service.update_refresh_scheduler(dm=dm)
        return response
