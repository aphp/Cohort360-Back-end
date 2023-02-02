import http
import logging

from django.db.models import Q
from django.http import HttpResponse, StreamingHttpResponse
from django_filters import rest_framework as filters, OrderingFilter
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from hdfs import HdfsError
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response

from admin_cohort.models import User
from admin_cohort.settings import COHORT_LIMIT
from admin_cohort.tools import join_qs
from admin_cohort.types import JobStatus
from admin_cohort.views import CustomLoggingMixin
from cohort.models import CohortResult
from exports import conf_exports
from exports.emails import check_email_address
from exports.models import ExportRequest
from exports.permissions import ExportRequestPermissions, ExportJupyterPermissions, can_review_transfer_jupyter, \
    can_review_export_csv
from exports.serializers import ExportRequestSerializer, ExportRequestSerializerNoReviewer, ExportRequestListSerializer
from exports.tasks import launch_request
from exports.types import ExportType

_log = logging.getLogger('django.request')


class ExportRequestFilter(filters.FilterSet):

    def multi_fields_filter(self, queryset, field, value: str):
        if value:
            return queryset.filter(join_qs([Q(cohort_fk__owner__firstname__icontains=value),
                                            Q(cohort_fk__owner__lastname__icontains=value)]))
        return queryset

    def multi_value_filter(self, queryset, field, value: str):
        if value:
            sub_values = [val.strip() for val in value.split(",")]
            return queryset.filter(join_qs([Q(**{field: v}) for v in sub_values]))
        return queryset

    cohort_name = filters.CharFilter(field_name="cohort_fk__name", lookup_expr='icontains')
    insert_datetime_gte = filters.DateTimeFilter(field_name="insert_datetime", lookup_expr='gte')
    insert_datetime_lte = filters.DateTimeFilter(field_name="insert_datetime", lookup_expr='lte')
    cohort_owner = filters.CharFilter(method="multi_fields_filter")
    output_format = filters.CharFilter(method="multi_value_filter", field_name="output_format")
    request_job_status = filters.CharFilter(method="multi_value_filter", field_name="request_job_status")

    ordering = OrderingFilter(fields=('insert_datetime',
                                      'output_format',
                                      ('owner__firstname', 'owner')))

    class Meta:
        model = ExportRequest
        fields = ('output_format', 'request_job_status', 'cohort_name', 'cohort_owner',
                  'creator_fk', 'target_unix_account', 'insert_datetime', 'owner')


class ExportRequestViewSet(CustomLoggingMixin, viewsets.ModelViewSet):
    queryset = ExportRequest.objects.all()
    serializer_class = ExportRequestSerializer
    lookup_field = "id"
    permissions = (ExportRequestPermissions, ExportJupyterPermissions)
    swagger_tags = ['Exports']
    pagination_class = LimitOffsetPagination
    filterset_class = ExportRequestFilter
    http_method_names = ['get', 'post', 'patch']
    logging_methods = ['POST', 'PATCH']
    search_fields = ("owner__firstname", "owner__lastname", "output_format",
                     "cohort_fk__name", "request_job_status", "target_name",
                     "target_unix_account__name")

    def should_log(self, request, response):
        act = getattr(getattr(request, "parser_context", {}).get("view", {}), "action", "")
        return request.method in self.logging_methods or act == "download"

    def get_serializer_context(self):
        return {'request': self.request}

    def get_serializer_class(self):
        if can_review_transfer_jupyter(self.request.user):
            return ExportRequestSerializer
        else:
            return ExportRequestSerializerNoReviewer

    def get_queryset(self):
        q = self.__class__.queryset
        reviewer = self.request.user
        types = []
        if can_review_export_csv(reviewer):
            types.append(ExportType.CSV)
        if can_review_transfer_jupyter(reviewer):
            types.extend([ExportType.PSQL, ExportType.HIVE])
        return q.filter(owner=self.request.user) | q.filter(output_format__in=types)

    @swagger_auto_schema(responses={'200': openapi.Response("List of export requests", ExportRequestListSerializer()),
                                    '204': openapi.Response("HTTP_204 if no export requests found")})
    def list(self, request, *args, **kwargs):
        q = self.filter_queryset(self.queryset)
        page = self.paginate_queryset(q)
        if page:
            serializer = ExportRequestListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['patch'], url_path="deny")
    def deny(self, request, *args, **kwargs):
        req: ExportRequest = self.get_object()
        reviewer = request.user

        if req.output_format == ExportType.CSV:
            if not can_review_export_csv(reviewer):
                raise PermissionDenied("L'utilisateur doit avoir le droit 'right_review_export_csv'")
        else:
            if not can_review_transfer_jupyter(reviewer):
                raise PermissionDenied("L'utilisateur doit avoir le droit 'right_review_transfer_jupyter'")

        if req.request_job_status == JobStatus.new:
            req.deny(request.user)
            req.request_job_status = JobStatus.denied   # to be deprecated
            # req.reviewer_id = reviewer_id
            req.save()
            return Response(self.serializer_class(req).data, status=status.HTTP_200_OK)
        else:
            raise ValidationError(f"La requête doit posséder le statut '{JobStatus.new}' pour être refusée. "
                                  f"Statut actuel : '{req.request_job_status}'")

    @action(detail=True, methods=['patch'], url_path="validate")
    def validate(self, request, *args, **kwargs):
        req: ExportRequest = self.get_object()
        reviewer = request.user

        if req.output_format == ExportType.HIVE and not can_review_transfer_jupyter(reviewer):
            raise PermissionDenied("L'utilisateur doit avoir le droit 'right_review_transfer_jupyter'")

        if req.output_format == ExportType.CSV and not can_review_export_csv(reviewer):
            raise PermissionDenied("L'utilisateur doit avoir le droit 'right_review_export_csv'")

        try:
            req.validate(request.user)
            launch_request.delay(req.id)
            return Response(self.serializer_class(req).data, status=status.HTTP_200_OK)
        except Exception as e:
            _log.exception(str(e))
            raise ValidationError("La requête n'a pas pu être validée")

    @swagger_auto_schema(
        request_body=openapi.Schema(type=openapi.TYPE_OBJECT,
                                    properties={'motivation': openapi.Schema(type=openapi.TYPE_STRING),
                                                'output_format': openapi.Schema(type=openapi.TYPE_STRING,
                                                                                description="hive, csv (default)"),
                                                'cohort_id': openapi.Schema(type=openapi.TYPE_STRING,
                                                                            description="use cohort_fk instead"),
                                                'provider_source_value': openapi.Schema(type=openapi.TYPE_STRING),
                                                'target_unix_account': openapi.Schema(type=openapi.TYPE_INTEGER),
                                                'tables': openapi.Schema(type=openapi.TYPE_ARRAY,
                                                                         items=openapi.Schema(
                                                                             type=openapi.TYPE_OBJECT,
                                                                             properties={
                                                                                 'omop_table_name': openapi.Schema(
                                                                                     type=openapi.TYPE_STRING)})),
                                                'nominative': openapi.Schema(type=openapi.TYPE_BOOLEAN,
                                                                             description="Default at False"),
                                                'shift_dates': openapi.Schema(type=openapi.TYPE_BOOLEAN,
                                                                              description="Default at False"),
                                                'cohort_fk': openapi.Schema(type=openapi.TYPE_STRING,
                                                                            description="Pk for a CohortResult"),
                                                'provider_id': openapi.Schema(type=openapi.TYPE_INTEGER,
                                                                              description='Deprecated'),
                                                'owner': openapi.Schema(type=openapi.TYPE_STRING,
                                                                        description="Pk for user that will receive the "
                                                                                    "export. WIll be set to the "
                                                                                    "request creator if undefined.")
                                                },
                                    required=["cohort_fk", "tables"]))
    def create(self, request, *args, **kwargs):
        # Local imports for mocking these functions during tests
        from exports.emails import email_info_request_confirmed

        if 'cohort_fk' in request.data:
            request.data['cohort'] = request.data.get('cohort_fk')
        elif 'cohort_id' in request.data:
            try:
                request.data['cohort'] = CohortResult.objects.get(fhir_group_id=request.data.get('cohort_id')).uuid
            except Exception:
                pass
        else:
            return Response(data="'cohort_fk' or 'cohort_id' is required",
                            status=status.HTTP_400_BAD_REQUEST)

        # todo: remove when front disables export button based on cohort's `exportable` field
        try:
            cohort_size = CohortResult.objects.get(uuid=request.data.get('cohort')).result_size
            if cohort_size and cohort_size > COHORT_LIMIT:
                return Response(data=f"Cannot export this large cohort. Current size limit: {COHORT_LIMIT}",
                                status=status.HTTP_400_BAD_REQUEST)
        except CohortResult.DoesNotExist:
            return Response(data="Invalid Cohort identifier",
                            status=status.HTTP_400_BAD_REQUEST)

        creator: User = request.user
        check_email_address(creator)

        owner_id = request.data.get('owner', request.data.get('provider_source_value', creator.pk))
        request.data['owner'] = owner_id

        # to deprecate
        try:
            request.data['provider_id'] = User.objects.get(pk=owner_id).provider_id
        except Exception:
            pass

        request.data['provider_source_value'] = owner_id
        request.data['creator_fk'] = creator.pk
        request.data['owner'] = request.data.get('owner', creator.pk)

        res: Response = super(ExportRequestViewSet, self).create(request, *args, **kwargs)
        if res.status_code == http.HTTPStatus.CREATED and res.data["request_job_status"] != JobStatus.failed:
            try:
                email_info_request_confirmed(res.data.serializer.instance, creator.email)
            except Exception as e:
                res.data['warning'] = f"L'email de confirmation n'a pas pu être envoyé à cause de l'erreur: {e}"
        return res

    @action(detail=True, methods=['get'], permission_classes=(ExportRequestPermissions,), url_path="download")
    def download(self, request, *args, **kwargs):
        req: ExportRequest = self.get_object()
        if req.request_job_status != JobStatus.finished:
            return HttpResponse("The export request you asked for is not done yet or has failed.",
                                status=http.HTTPStatus.FORBIDDEN)
        if req.output_format != ExportType.CSV:
            return HttpResponse(f"Can only download results of {ExportType.CSV} type. Got {req.output_format} instead",
                                status=http.HTTPStatus.FORBIDDEN)
        user: User = self.request.user
        if req.owner.pk != user.pk:
            raise PermissionDenied("L'utilisateur n'est pas à l'origine de l'export")

        # start_bytes = re.search(r'bytes=(\d+)-',
        #                         request.META.get('HTTP_RANGE', ''), re.S)
        # start_bytes = int(start_bytes.group(1)) if start_bytes else 0
        try:
            response = StreamingHttpResponse(conf_exports.stream_gen(req.target_full_path))
            resp_size = conf_exports.get_file_size(req.target_full_path)

            response['Content-Type'] = 'application/zip'
            response['Content-Length'] = resp_size
            response['Content-Disposition'] = f"attachment; filename=export_{req.cohort_id}.zip"
            # response['Content-Range'] = 'bytes %d-%d/%d' % (
            #     start_bytes, resp_size, resp_size
            # )
            return response
        except HdfsError as e:
            _log.exception(e.message)
            return HttpResponse(e.message, status=http.HTTPStatus.INTERNAL_SERVER_ERROR)
        except conf_exports.HdfsServerUnreachableError:
            return HttpResponse("HDFS servers are unreachable or in stand-by",
                                status=http.HTTPStatus.INTERNAL_SERVER_ERROR)
