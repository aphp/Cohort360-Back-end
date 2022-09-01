import re

import django_filters
from django.db.models import F
from django.http import QueryDict
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.decorators import action
from rest_framework import status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.relations import PrimaryKeyRelatedField
from rest_framework.response import Response
from rest_framework_extensions.mixins import NestedViewSetMixin

from admin_cohort.types import JobStatus, NewJobStatus
from admin_cohort.views import SwaggerSimpleNestedViewSetMixin, \
    CustomLoggingMixin
from cohort.permissions import IsOwner, OR, IsAdmin
from admin_cohort import app
from cohort.conf_cohort_job_api import cancel_job, \
    get_fhir_authorization_header
from cohort.models import Request, CohortResult, RequestQuerySnapshot, \
    DatedMeasure, Folder, User
from cohort.serializers import RequestSerializer, \
    CohortResultSerializer, RequestQuerySnapshotSerializer, \
    DatedMeasureSerializer, FolderSerializer, \
    CohortResultSerializerFullDatedMeasure


class NoUpdateViewSetMixin:
    def update(self, request, *args, **kwargs):
        return Response(
            {"response": "request_query_snapshot manual update not possible"},
            status=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, *args, **kwargs):
        return Response(
            {"response": "request_query_snapshot manual update not possible"},
            status=status.HTTP_400_BAD_REQUEST)


class CustomOrderingFilter(OrderingFilter):
    # Allows to add aliases while ordering
    # for instance, you can add in a url /?ordering=alias
    # and set the viewset's ordering_fields to ("alias", "actual_field")
    def remove_invalid_fields(self, queryset, fields, view, request):
        valid_fields = self.get_valid_fields(queryset, view,
                                             {'request': request})
        valid_terms = [
            term for term in fields
            if term.lstrip('-') in [vf[0] for vf in valid_fields]
            and re.compile(r'\?|[-+]?[.\w]+$').match(term)
        ]
        for term in valid_terms:
            ordering_term = [v_f[1] for v_f in valid_fields
                             if v_f[0] == term.lstrip('-')][0]
            yield f"-{ordering_term}" if term[0] == '-' else ordering_term


class BaseViewSet(viewsets.ModelViewSet):
    filter_backends = (DjangoFilterBackend, CustomOrderingFilter, SearchFilter,)

    def get_serializer_context(self):
        return {'request': self.request}


class UserObjectsRestrictedViewSet(BaseViewSet):
    def get_queryset(self):
        return self.__class__.queryset.filter(owner=self.request.user)

    def create(self, request, *args, **kwargs):
        user = request.user
        if type(request.data) == QueryDict:
            request.data._mutable = True

        request.data['owner'] = request.data.get(
            'owner', request.data.get('owner_id', user.pk))

        return super(UserObjectsRestrictedViewSet, self).create(
            request, *args, **kwargs)

    def initial(self, request, *args, **kwargs):
        super(UserObjectsRestrictedViewSet, self)\
            .initial(request, *args, **kwargs)

        s = self.get_serializer_class()()
        primary_key_fields = [f.field_name for f in s._writable_fields
                              if isinstance(f, PrimaryKeyRelatedField)]

        if isinstance(request.data, QueryDict):
            request.data._mutable = True

        for field_name in primary_key_fields:
            field_name_with_id = f'{field_name}_id'
            if field_name_with_id in request.data:
                request.data[field_name] = request.data[field_name_with_id]


class CohortFilter(django_filters.FilterSet):
    def perimeter_filter(self, queryset, field, value):
        return queryset.filter(
            request_query_snapshot__perimeters_ids__contains=[value])

    def perimeters_filter(self, queryset, field, value):
        return queryset.filter(
            request_query_snapshot__perimeters_ids__contains=value.split(","))

    name = django_filters.CharFilter(field_name='name', lookup_expr="icontains")
    min_result_size = django_filters.NumberFilter(
        field_name='dated_measure__measure', lookup_expr='gte')
    max_result_size = django_filters.NumberFilter(
        field_name='dated_measure__measure', lookup_expr='lte')
    # ?min_created_at=2015-04-23
    min_fhir_datetime = django_filters.IsoDateTimeFilter(
        field_name='dated_measure__fhir_datetime', lookup_expr="gte")
    max_fhir_datetime = django_filters.IsoDateTimeFilter(
        field_name='dated_measure__fhir_datetime', lookup_expr="lte")
    request_job_status = django_filters.AllValuesMultipleFilter()

    # unused, untested
    type = django_filters.AllValuesMultipleFilter()
    perimeter_id = django_filters.CharFilter(method="perimeter_filter")
    perimeters_ids = django_filters.CharFilter(method="perimeters_filter")

    class Meta:
        model = CohortResult
        fields = (
            "name",
            "min_result_size",
            "max_result_size",
            "min_fhir_datetime",
            "max_fhir_datetime",
            "favorite",
            "type",
            "fhir_group_id",
            "create_task_id",
            "request_query_snapshot",
            "request_query_snapshot__request",
            "new_request_job_status",
            "request_job_status",
            "perimeter_id",
            "perimeters_ids",
        )


class CohortResultViewSet(NestedViewSetMixin, UserObjectsRestrictedViewSet):
    queryset = CohortResult.objects\
        .select_related('request_query_snapshot__request')\
        .annotate(request_id=F('request_query_snapshot__request__uuid')).all()
    serializer_class = CohortResultSerializer
    http_method_names = ['get', 'post', 'patch', 'delete']
    lookup_field = "uuid"
    swagger_tags = ['Cohort - cohorts']

    pagination_class = LimitOffsetPagination

    filter_class = CohortFilter
    ordering_fields = (
        "name",
        ("result_size", "dated_measure__measure"),
        ("fhir_datetime", "dated_measure__fhir_datetime"),
        "type",
        "favorite",
        "request_job_status"
    )
    # ordering = ('-created_at',)
    search_fields = ('$name', '$description',)

    def get_permissions(self):
        if self.request.method in ['GET', 'POST', 'PATCH', 'DELETE']:
            return OR(IsOwner())

    def get_serializer_class(self):
        if self.request.method in ["POST", "PUT", "PATCH"] \
                and "dated_measure" in self.request.data \
                and isinstance(self.request.data["dated_measure"], dict):
            return CohortResultSerializerFullDatedMeasure
        if self.request.method == "GET":
            return CohortResultSerializerFullDatedMeasure
        return super(CohortResultViewSet, self).get_serializer_class()

    def create(self, request, *args, **kwargs):
        if type(request.data) == QueryDict:
            request.data._mutable = True

        if 'request_query_snapshot' in kwargs:
            request.data["request_query_snapshot"] = \
                kwargs['request_query_snapshot']

        if 'dated_measure_id' not in request.data:
            if 'dated_measure' in request.data:
                dated_measure = request.data['dated_measure']
                if isinstance(dated_measure, dict):
                    if "request_query_snapshot" in request.data:
                        dated_measure["request_query_snapshot"] \
                            = request.data["request_query_snapshot"]
        else:
            request.data['dated_measure'] = request.data['dated_measure_id']

        return super(CohortResultViewSet, self).create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(
            instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        # todo : check
        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}

        return Response(serializer.data)


class NestedCohortResultViewSet(SwaggerSimpleNestedViewSetMixin,
                                CohortResultViewSet):
    pass


class DatedMeasureViewSet(NestedViewSetMixin, UserObjectsRestrictedViewSet):
    queryset = DatedMeasure.objects\
        .select_related('request_query_snapshot__request')\
        .annotate(request_id=F('request_query_snapshot__request__uuid')).all()
    serializer_class = DatedMeasureSerializer
    http_method_names = ['get', 'post', 'patch', 'delete']
    lookup_field = "uuid"
    swagger_tags = ['Cohort - dated-measures']

    pagination_class = LimitOffsetPagination

    filterset_fields = ("uuid", "request_query_snapshot",
                        "request_query_snapshot__request", "mode",
                        "count_task_id")
    ordering_fields = ("created_at", "modified_at", "result_size")
    ordering = ("-created_at",)
    search_fields = []

    def get_permissions(self):
        if self.request.method in ['GET', 'POST', 'PATCH', 'DELETE']:
            return OR(IsOwner())
        else:
            return OR(IsAdmin())

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if CohortResult.objects.filter(
                dated_measure__uuid=instance.uuid).first() is not None:
            return Response({
                'message': "Cannot delete a Dated measure "
                           "that is binded to a cohort result"
            }, status=status.HTTP_403_FORBIDDEN)
        return super(DatedMeasureViewSet, self)\
            .destroy(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        if type(request.data) == QueryDict:
            request.data._mutable = True

        if 'request_query_snapshot' in kwargs:
            request.data["request_query_snapshot"] \
                = kwargs['request_query_snapshot']

        return super(DatedMeasureViewSet, self).create(request, *args, **kwargs)

    @action(methods=['post'], detail=False, url_path='create-unique')
    def create_unique(self, request, *args, **kwargs):
        """
        Demande à l'API FHIR d'annuler tous les jobs de calcul de count liés à
        une construction de Requête avant d'en créer un nouveau
        """
        # TODO : test
        if 'request_query_snapshot' in kwargs:
            rqs_id = kwargs['request_query_snapshot']
        elif "request_query_snapshot_id" in request.data:
            rqs_id = request.data.get('request_query_snapshot_id')
        else:
            return Response(
                dict(message="'request_query_snapshot_id' not provided"),
                status.HTTP_400_BAD_REQUEST,
            )

        headers = get_fhir_authorization_header(request)
        try:
            rqs: RequestQuerySnapshot = RequestQuerySnapshot.objects.get(
                pk=rqs_id
            )
        except RequestQuerySnapshot.DoesNotExist:
            return Response(
                dict(
                    message="No existing request_query_snapshot to "
                            "'request_query_snapshot_id' provided"
                ),
                status.HTTP_400_BAD_REQUEST,
            )

        req_dms = rqs.request.dated_measures
        for job_to_cancel in (req_dms.filter(
                request_job_status=JobStatus.STARTED.name.lower()
        ) | req_dms.filter(
            new_request_job_status=NewJobStatus.new.name.lower()
        )).prefetch_related('cohort', 'restricted_cohort'):
            if len(job_to_cancel.cohort.all()) \
                    or len(job_to_cancel.restricted_cohort.all()):
                # if the pending dated measure is bound to a cohort,
                # we don't cancel it
                continue
            try:
                job_status = cancel_job(job_to_cancel.request_job_id, headers)
                job_to_cancel.request_job_status = job_status.value
                job_to_cancel.save()
            except Exception as e:
                return Response(
                    dict(
                        message=f"Error while cancelling job "
                                f"'{job_to_cancel.request_job_id}', bound "
                                f"to dated-measure '{job_to_cancel.uuid}': "
                                f"{str(e)}"
                    ), status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        for job_to_cancel in (req_dms.filter(
                request_job_status=JobStatus.PENDING.name.lower()
        ) | req_dms.filter(
            new_request_job_status=NewJobStatus.new.name.lower()
        )).prefetch_related('cohort', 'restricted_cohort'):
            if len(job_to_cancel.cohort.all()) \
                    or len(job_to_cancel.restricted_cohort.all()):
                # if the pending dated measure is bound to a cohort,
                # we don't cancel it
                continue

            try:
                app.control.revoke(job_to_cancel.count_task_id)
                # revoke(task_id=job_to_cancel.count_task_id, terminate=True)
                job_to_cancel.request_job_status = JobStatus.KILLED.name.lower()
                job_to_cancel.new_request_job_status = (NewJobStatus.cancelled
                                                        .value)
                job_to_cancel.save()
            except Exception as e:
                return Response(
                    dict(message=str(e)), status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        return self.create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        return Response("Updating a dated measure is not allowed",
                        status=status.HTTP_403_FORBIDDEN)

    @action(methods=['patch'], detail=True, url_path='abort')
    def abort(self, request, *args, **kwargs):
        """
        Demande à l'API FHIR d'annuler le job de calcul de count d'une requête
        """
        # TODO : test
        instance: DatedMeasure = self.get_object()
        try:
            cancel_job(
                instance.request_job_id,
                get_fhir_authorization_header(request)
            )
        except Exception as e:
            return Response(
                dict(message=str(e)),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class NestedDatedMeasureViewSet(SwaggerSimpleNestedViewSetMixin,
                                DatedMeasureViewSet):

    @swagger_auto_schema(auto_schema=None)
    def abort(self, request, *args, **kwargs):
        return self.abort(self, request, *args, **kwargs)


class RequestQuerySnapshotViewSet(
    NestedViewSetMixin, NoUpdateViewSetMixin,
    UserObjectsRestrictedViewSet
):
    queryset = RequestQuerySnapshot.objects.all()
    serializer_class = RequestQuerySnapshotSerializer
    http_method_names = ['get', 'post']
    lookup_field = "uuid"
    swagger_tags = ['Cohort - request-query-snapshots']

    pagination_class = LimitOffsetPagination

    filterset_fields = ('uuid', 'request_id', 'request', 'is_active_branch',
                        'shared_by', "previous_snapshot", "request",
                        "request__parent_folder")
    ordering_fields = ('created_at', 'modified_at',)
    ordering = ('-created_at',)
    search_fields = ('$serialized_query',)

    def get_permissions(self):
        if self.request.method in ['GET', 'POST', 'PATCH', 'DELETE']:
            return OR(IsOwner())

    def create(self, request, *args, **kwargs):
        if type(request.data) == QueryDict:
            request.data._mutable = True

        if 'request_id' in kwargs:
            request.data["request"] = kwargs['request_id']
        if 'previous_snapshot' in kwargs:
            request.data["previous_snapshot"] = kwargs['previous_snapshot']

        return super(RequestQuerySnapshotViewSet, self)\
            .create(request, *args, **kwargs)

    def list(self, request, *args, **kwargs):
        return super(RequestQuerySnapshotViewSet, self)\
            .list(request, *args, **kwargs)

    @action(detail=True, methods=['post'], permission_classes=(IsOwner,),
            url_path="save")
    def save(self, req, request_query_snapshot_uuid):
        # unused, untested
        try:
            rqs = RequestQuerySnapshot.objects.get(
                uuid=request_query_snapshot_uuid)
        except RequestQuerySnapshot.DoesNotExist:
            return Response({"response": "request_query_snapshot not found"},
                            status=status.HTTP_404_NOT_FOUND)
        rqs.save_snapshot()
        return Response({'response': "Query successful!"},
                        status=status.HTTP_200_OK)

    @swagger_auto_schema(
        method='post',
        operation_summary="Share RequestQuerySnapshot with a User by creating "
                          "a new Request in its Shared Folder. \n"
                          "'recipients' are strings joined with ','\n"
                          "'name' is optional",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "recipients": openapi.Schema(type=openapi.TYPE_STRING),
                "name": openapi.Schema(type=openapi.TYPE_STRING),
            }),
        responses={
            '201': openapi.Response(
                "New requests created for recipients",
                RequestQuerySnapshotSerializer(many=True)),
            '400': openapi.Response("One or more recipient's not found"),
            '404': openapi.Response("RequestQuerySnapshot not found "
                                    "(possibly not owned)")
        })
    @action(detail=True, methods=['post'], permission_classes=(IsOwner,),
            url_path="share")
    def share(self, request, *args, **kwargs):
        recipients = request.data.get('recipients', None)
        if recipients is None:
            raise ValidationError("'recipients' doit être fourni")

        recipients = recipients.split(",")
        name = request.data.get('name', None)

        users = User.objects.filter(pk__in=recipients)
        users_ids = [str(u.pk) for u in users]
        errors = []

        for r in recipients:
            if r not in users_ids:
                errors.append(r)

        if len(errors):
            raise ValidationError(
                f"Les utilisateur.rices avec les ids suivants "
                f"n'ont pas été trouvés: {','.join(errors)}")

        rqs: RequestQuerySnapshot = self.get_object()
        rqss = rqs.share(users, name)
        return Response(RequestQuerySnapshotSerializer(rqss, many=True).data,
                        status=status.HTTP_201_CREATED)


class NestedRqsViewSet(SwaggerSimpleNestedViewSetMixin,
                       RequestQuerySnapshotViewSet):
    @swagger_auto_schema(auto_schema=None)
    def save(self, req, request_query_snapshot_uuid):
        return self.save(req, request_query_snapshot_uuid)

    @swagger_auto_schema(auto_schema=None)
    def share(self, request, *args, **kwargs):
        return self.share(request, *args, **kwargs)


class RequestViewSet(NestedViewSetMixin, UserObjectsRestrictedViewSet):
    queryset = Request.objects.all()
    serializer_class = RequestSerializer
    http_method_names = ["get", "post", "patch", "delete"]
    lookup_field = "uuid"
    swagger_tags = ["Cohort - requests"]

    pagination_class = LimitOffsetPagination

    filterset_fields = ("uuid", "name", "favorite", "data_type_of_query",
                        "parent_folder", "shared_by")
    ordering_fields = ("created_at", "modified_at",
                       "name", "favorite", "data_type_of_query")
    ordering = ("name",)
    search_fields = ("$name", "$description",)

    def get_permissions(self):
        if self.request.method in ["GET", "POST", "PATCH", "DELETE"]:
            return OR(IsOwner())

    def create(self, request, *args, **kwargs):
        if type(request.data) == QueryDict:
            request.data._mutable = True

        if 'parent_folder' in kwargs:
            request.data["parent_folder"] = kwargs['parent_folder']

        return super(RequestViewSet, self).create(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        return super(RequestViewSet, self)\
            .partial_update(request, *args, **kwargs)


class NestedRequestViewSet(SwaggerSimpleNestedViewSetMixin, RequestViewSet):
    pass


class FolderViewSet(CustomLoggingMixin, NestedViewSetMixin,
                    UserObjectsRestrictedViewSet):
    queryset = Folder.objects.all()
    serializer_class = FolderSerializer
    http_method_names = ['get', 'post', 'patch', 'delete']
    lookup_field = "uuid"

    swagger_tags = ['Cohort - folders']
    logging_methods = ['POST', 'PUT', 'PATCH', 'DELETE']
    pagination_class = LimitOffsetPagination

    filterset_fields = ('uuid', 'name', 'parent_folder')
    ordering_fields = ('created_at', 'modified_at',
                       'name')
    ordering = ('name',)
    search_fields = ('$name', '$description',)

    def get_permissions(self):
        if self.request.method in ['GET', 'POST', 'PATCH', 'DELETE']:
            return OR(IsOwner())
