import logging
from io import BytesIO

from django.db import transaction
from django.http import FileResponse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from cohort.models import FeasibilityStudy
from cohort.serializers import FeasibilityStudySerializer, FeasibilityStudyCreateSerializer, FeasibilityStudyPatchSerializer
from cohort.services.feasibility_study import feasibility_study_service
from cohort.views.shared import UserObjectsRestrictedViewSet

_logger = logging.getLogger('info')
_logger_err = logging.getLogger('django.request')


@extend_schema_view(
    list=extend_schema(exclude=True),
    retrieve=extend_schema(exclude=True)
)
class FeasibilityStudyViewSet(UserObjectsRestrictedViewSet):
    queryset = FeasibilityStudy.objects.all()
    serializer_class = FeasibilityStudySerializer
    http_method_names = ['get', 'post', 'patch']
    swagger_tags = ['Feasibility Studies']

    def get_permissions(self):
        special_permissions = feasibility_study_service.get_special_permissions(self.request)
        if special_permissions:
            return special_permissions
        return super().get_permissions()

    def get_queryset(self):
        if feasibility_study_service.allow_use_full_queryset(request=self.request):
            return self.queryset
        return super().get_queryset()

    @extend_schema(request=FeasibilityStudyCreateSerializer,
                   responses={status.HTTP_201_CREATED: FeasibilityStudySerializer})
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        transaction.on_commit(lambda: feasibility_study_service.handle_feasibility_study_count(request=request,
                                                                                               fs=response.data.serializer.instance))
        return response

    @extend_schema(request=FeasibilityStudyPatchSerializer,
                   responses={status.HTTP_200_OK: FeasibilityStudySerializer})
    def partial_update(self, request, *args, **kwargs):
        try:
            feasibility_study_service.handle_patch_feasibility_study(fs=self.get_object(),
                                                                     data=request.data)
        except ValueError as ve:
            return Response(data=f"{ve}", status=status.HTTP_400_BAD_REQUEST)
        response = super().partial_update(request, *args, **kwargs)
        return response

    @extend_schema(responses={(status.HTTP_200_OK, "application/zip"): OpenApiTypes.BINARY})
    @action(detail=True, methods=['get'], url_path='download')
    def download_report(self, request, *args, **kwargs):
        fs = self.get_object()
        if not fs.report_file:
            return Response(data="Report not found", status=status.HTTP_404_NOT_FOUND)
        file_name = feasibility_study_service.get_file_name(fs=fs)
        response = FileResponse(BytesIO(fs.report_file), content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="{file_name}.zip"'
        return response
