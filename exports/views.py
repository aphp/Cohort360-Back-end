import http

import django_filters
from django.http import HttpResponse, StreamingHttpResponse
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from hdfs import HdfsError
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from admin_cohort.models import User, NewJobStatus
from admin_cohort.permissions import OR
from admin_cohort.types import JobStatus
from admin_cohort.views import CustomLoggingMixin
from cohort.models import CohortResult
from cohort.permissions import IsOwner
from workspaces.conf_workspaces import get_account_groups_from_id_aph
from workspaces.permissions import AccountPermissions
from workspaces.views import AccountViewset
from exports import conf_exports
from exports.emails import check_email_address
from exports.models import ExportRequest, ExportType, NEW_STATUS, \
    VALIDATED_STATUS, DENIED_STATUS
from exports.permissions import ExportRequestPermissions, \
    can_review_transfer_jupyter, can_review_export_csv, AnnexesPermissions, \
    ExportJupyterPermissions
from exports.serializers import ExportRequestSerializer, \
    AnnexeAccountSerializer, AnnexeCohortResultSerializer, \
    ExportRequestSerializerNoReviewer


class UserFilter(django_filters.FilterSet):
    def provider_source_value_filter(self, queryset, field, value):
        return queryset.filter(
            aphp_ldap_group_dn__in=get_account_groups_from_id_aph(value))

    provider_source_value = django_filters.CharFilter(
        field_name='provider_source_value',
        method="provider_source_value_filter")

    class Meta:
        model = User
        fields = ("provider_source_value",)


class UsersViewSet(AccountViewset):
    lookup_field = "uid"
    serializer_class = AnnexeAccountSerializer
    http_method_names = ["get"]

    swagger_tags = ['Exports - users']
    filter_class = UserFilter

    def get_permissions(self):
        return OR(AnnexesPermissions(),
                  AccountPermissions())

    def get_queryset(self):
        q = super(AccountViewset, self).get_queryset()
        user = self.request.user
        if not can_review_transfer_jupyter(user)\
                and not can_review_export_csv(user):
            ad_groups = get_account_groups_from_id_aph(user)
            return q.filter(aphp_ldap_group_dn__in=ad_groups)
        return q

    def list(self, request, *args, **kwargs):
        return super(UsersViewSet, self).list(request, *args, **kwargs)


class CohortFilter(django_filters.FilterSet):
    class Meta:
        model = CohortResult
        fields = ('owner_id',)


class CohortViewSet(viewsets.ModelViewSet):
    lookup_field = "uuid"
    http_method_names = ["get"]
    serializer_class = AnnexeCohortResultSerializer
    queryset = CohortResult.objects.filter(
        request_job_status=JobStatus.FINISHED
    ) | CohortResult.objects.filter(
        new_request_job_status=NewJobStatus.finished
    )

    swagger_tags = ['Exports - cohorts']
    filter_class = CohortFilter
    search_fields = ('$name', '$description',)

    def get_permissions(self):
        return OR(AnnexesPermissions(), IsOwner())

    def get_queryset(self):
        user = self.request.user
        if not can_review_transfer_jupyter(user)\
                and not can_review_export_csv(user):
            return self.queryset.filter(owner_id=user)

        return self.queryset

    @swagger_auto_schema(
        manual_parameters=list(map(
            lambda x: openapi.Parameter(
                name=x[0], in_=openapi.IN_QUERY, description=x[1], type=x[2],
                pattern=x[3] if len(x) == 4 else None
            ), [
                ["owner_id", "Filter type",
                 openapi.TYPE_STRING],
                [
                    "search",
                    f"Will search in multiple fields "
                    f"({', '.join(search_fields)})", openapi.TYPE_STRING
                ],
            ])))
    def list(self, request, *args, **kwargs):
        return super(CohortViewSet, self).list(request, *args, **kwargs)


class ExportRequestFilter(django_filters.FilterSet):
    class Meta:
        model = ExportRequest
        fields = ('output_format', 'status', 'creator_fk')


class ExportRequestViewset(CustomLoggingMixin, viewsets.ModelViewSet):
    serializer_class = ExportRequestSerializer
    queryset = ExportRequest.objects.all()
    lookup_field = "id"
    permissions = (ExportRequestPermissions, ExportJupyterPermissions)

    swagger_tags = ['Exports']
    logging_methods = ['POST', 'PATCH']
    filterset_class = ExportRequestFilter
    http_method_names = ['get', 'post', 'patch']

    def should_log(self, request, response):
        action = getattr(
            getattr(request, "parser_context", {}).get("view", {}),
            "action", ""
        )
        return (
            request.method in self.logging_methods
        ) or action == "download"

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

        return (q.filter(owner=self.request.user)
                | q.filter(output_format__in=types))

    @action(
        detail=True, methods=['patch'], url_path="deny"
    )
    def deny(self, request, *args, **kwargs):
        req: ExportRequest = self.get_object()
        reviewer = request.user

        if req.output_format == ExportType.CSV:
            if not can_review_export_csv(reviewer):
                raise PermissionDenied("L'utilisateur doit avoir le droit "
                                       "'right_review_export_csv'")
        else:
            if not can_review_transfer_jupyter(reviewer):
                raise PermissionDenied("L'utilisateur doit avoir le droit "
                                       "'right_review_transfer_jupyter'")

        req: ExportRequest = self.get_object()
        if req.status == NEW_STATUS:
            req.deny(request.user)

            # to be deprecated
            req.status = DENIED_STATUS
            # req.reviewer_id = reviewer_id

            req.save()
            return Response(self.serializer_class(req).data,
                            status=status.HTTP_200_OK)
        else:
            raise ValidationError(f"La requête doit posséder le statut "
                                  f"'{NEW_STATUS}' pour être refusée. "
                                  f"Statut actuel : '{req.status}'")

    @action(
        detail=True, methods=['patch'], url_path="validate"
    )
    def validate(self, request, *args, **kwargs):
        req: ExportRequest = self.get_object()
        reviewer = request.user

        if req.output_format == ExportType.HIVE \
                and not can_review_transfer_jupyter(reviewer):
            raise PermissionDenied("L'utilisateur doit avoir le droit "
                                   "'right_review_transfer_jupyter'")

        if req.output_format == ExportType.CSV \
                and not can_review_export_csv(reviewer):
            raise PermissionDenied("L'utilisateur doit avoir le droit "
                                   "'right_review_export_csv'")

        try:
            req.validate(request.user)

            # to be deprecated
            req.status = VALIDATED_STATUS

            req.save()

            from exports.tasks import launch_request
            launch_request.delay(req.id)

            return Response(self.serializer_class(req).data,
                            status=status.HTTP_200_OK)
        except Exception as e:
            raise ValidationError(f"La requête n'a pas pu être validée: {e}")

    @swagger_auto_schema(request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'motivation': openapi.Schema(type=openapi.TYPE_STRING),
            'output_format': openapi.Schema(
                type=openapi.TYPE_STRING, description="hive, csv (default)"),
            'cohort_id': openapi.Schema(
                type=openapi.TYPE_STRING,
                description="(to deprecate, use cohort_fk instead)"),
            'provider_source_value': openapi.Schema(type=openapi.TYPE_STRING),
            'target_unix_account': openapi.Schema(type=openapi.TYPE_INTEGER),
            'tables': openapi.Schema(
                type=openapi.TYPE_ARRAY, items=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'omop_table_name': openapi.Schema(
                            type=openapi.TYPE_STRING),
                    })),
            'nominative': openapi.Schema(
                type=openapi.TYPE_BOOLEAN, description="Default at False"),
            'shift_dates': openapi.Schema(
                type=openapi.TYPE_BOOLEAN, description="Default at False"),
            'cohort_fk': openapi.Schema(
                type=openapi.TYPE_STRING, description="Primary key for "
                                                      "a CohortResult"),
            'provider_id': openapi.Schema(
                type=openapi.TYPE_INTEGER, description='Deprecated'),
            'owner': openapi.Schema(
                type=openapi.TYPE_STRING,
                description="Primary Key for user that will receive the export."
                            "WIll be set to the request creator if undefined."),
        }, required=["cohort_fk", "tables"]))
    def create(self, request, *args, **kwargs):
        # Local imports for mocking these functions during tests
        from exports.emails import email_info_request_confirmed

        creator: User = request.user
        check_email_address(creator)

        owner_id = request.data.get(
            'owner', request.data.get('provider_source_value', creator.pk))
        request.data['owner'] = owner_id

        # to deprecate
        try:
            request.data['provider_id'] = \
                User.objects.get(pk=owner_id).provider_id
        except Exception:
            pass

        if 'cohort_fk' in request.data:
            request.data['cohort'] = request.data.get('cohort_fk')
        elif 'cohort_id' in request.data:
            try:
                request.data['cohort'] = CohortResult.objects.get(
                    fhir_group_id=request.data.get('cohort_id')).uuid
            except Exception:
                pass
        else:
            raise ValidationError("'cohort_fk' or 'cohort_id' is required")

        request.data['provider_source_value'] = owner_id
        request.data['creator_fk'] = creator.pk
        request.data['owner'] = request.data.get('owner', creator.pk)

        res: Response = super(ExportRequestViewset, self)\
            .create(request, *args, **kwargs)
        if res.status_code == http.HTTPStatus.CREATED \
                and res.data["new_request_job_status"] != NewJobStatus.failed:
            try:
                email_info_request_confirmed(res.data.serializer.instance,
                                             creator.email)
            except Exception as e:
                res.data['warning'] = f"L'email de confirmation n'a pas pu " \
                                      f"être envoyé à cause de l'erreur " \
                                      f"suivante : {e}"
        return res

    @action(
        detail=True, methods=['get'],
        permission_classes=(ExportRequestPermissions,), url_path="download"
    )
    def download(self, request, *args, **kwargs):
        req: ExportRequest = self.get_object()
        if req.new_request_job_status != NewJobStatus.finished:
            return HttpResponse("The export request you asked for is not "
                                "done yet or has failed.",
                                status=http.HTTPStatus.FORBIDDEN)
        if req.output_format != ExportType.CSV:
            return HttpResponse(f"Can only download results of "
                                f"{ExportType.CSV.value} type "
                                f"(this one is {req.output_format}).",
                                status=http.HTTPStatus.FORBIDDEN)
        user: User = self.request.user
        if req.owner.pk != user.pk:
            raise PermissionDenied("L'utilisateur n'est pas à "
                                   "l'origine de l'export")

        # start_bytes = re.search(r'bytes=(\d+)-',
        #                         request.META.get('HTTP_RANGE', ''), re.S)
        # start_bytes = int(start_bytes.group(1)) if start_bytes else 0
        try:
            response = StreamingHttpResponse(
                conf_exports.stream_gen(req.target_full_path))
            resp_size = conf_exports.get_file_size(req.target_full_path)

            response['Content-Type'] = 'application/zip'
            response['Content-Length'] = resp_size
            response[
                'Content-Disposition'] = f"attachment; filename=export_" \
                                         f"{req.cohort_id}.zip"
            # response['Content-Range'] = 'bytes %d-%d/%d' % (
            #     start_bytes, resp_size, resp_size
            # )
            return response
        except HdfsError as e:
            return HttpResponse(e, status=http.HTTPStatus.INTERNAL_SERVER_ERROR)
        except conf_exports.HdfsServerUnreachableError:
            return HttpResponse(
                "Hdfs servers are unreachable or in stand-by",
                status=http.HTTPStatus.INTERNAL_SERVER_ERROR
            )
