import logging
from io import BytesIO

from django.db import transaction
from django.http import FileResponse
from django_filters import rest_framework as filters, OrderingFilter
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from admin_cohort.tools.cache import cache_response
from admin_cohort.tools.negative_limit_paginator import NegativeLimitOffsetPagination
from cohort.models import FeasibilityStudy
from cohort.serializers import FeasibilityStudySerializer
from cohort.services.feasibility_study import feasibility_study_service
from cohort.views.shared import UserObjectsRestrictedViewSet

_logger = logging.getLogger('info')
_logger_err = logging.getLogger('django.request')


class FeasibilityStudyFilter(filters.FilterSet):
    ordering = OrderingFilter(fields=("-created_at",))

    class Meta:
        model = FeasibilityStudy
        fields = ["created_at"]


class FeasibilityStudyViewSet(UserObjectsRestrictedViewSet):
    queryset = FeasibilityStudy.objects.all()
    serializer_class = FeasibilityStudySerializer
    http_method_names = ['get', 'post', 'patch']
    lookup_field = "uuid"
    swagger_tags = ['Cohort - feasibility-studies']
    filterset_class = FeasibilityStudyFilter
    pagination_class = NegativeLimitOffsetPagination

    def get_permissions(self):
        special_permissions = feasibility_study_service.get_special_permissions(self.request)
        if special_permissions:
            return special_permissions
        return super(FeasibilityStudyViewSet, self).get_permissions()

    def get_queryset(self):
        if feasibility_study_service.allow_use_full_queryset(request=self.request):
            return self.queryset
        return super(FeasibilityStudyViewSet, self).get_queryset()

    @cache_response()
    def list(self, request, *args, **kwargs):
        return super(FeasibilityStudyViewSet, self).list(request, *args, **kwargs)

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        transaction.on_commit(lambda: feasibility_study_service.handle_feasibility_study_count(request=request,
                                                                                               fs=response.data.serializer.instance))
        return response

    def partial_update(self, request, *args, **kwargs):
        try:
            feasibility_study_service.handle_patch_feasibility_study(fs=self.get_object(),
                                                                     data=request.data)
        except ValueError as ve:
            return Response(data=f"{ve}", status=status.HTTP_400_BAD_REQUEST)
        response = super(FeasibilityStudyViewSet, self).partial_update(request, *args, **kwargs)
        return response

    @action(detail=True, methods=['get'], url_path='download')
    def download_report(self, request, *args, **kwargs):
        fs = self.get_object()
        if not fs.report_file:
            return Response(data="Report not found", status=status.HTTP_404_NOT_FOUND)
        file_name = feasibility_study_service.get_file_name(fs=fs)
        response = FileResponse(BytesIO(fs.report_file), content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="{file_name}.zip"'
        return response
