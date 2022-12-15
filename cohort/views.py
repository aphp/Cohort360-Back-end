import logging

from django.db.models import F
from django.db.models import Q
from django.http import QueryDict, JsonResponse, HttpResponse, Http404, HttpResponseServerError, HttpResponseBadRequest
from django_filters import OrderingFilter
from django_filters import rest_framework as filters
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.relations import RelatedField
from rest_framework.response import Response
from rest_framework_extensions.mixins import NestedViewSetMixin

from accesses.models import get_user_valid_manual_accesses_queryset
from admin_cohort import app
from admin_cohort.tools import join_qs
from admin_cohort.types import JobStatus
from admin_cohort.views import SwaggerSimpleNestedViewSetMixin, CustomLoggingMixin
from cohort.conf_cohort_job_api import cancel_job, get_fhir_authorization_header
from cohort.models import Request, CohortResult, RequestQuerySnapshot, DatedMeasure, Folder, User
from cohort.permissions import IsOwner
from cohort.serializers import RequestSerializer, CohortResultSerializer, RequestQuerySnapshotSerializer, \
    DatedMeasureSerializer, FolderSerializer, CohortResultSerializerFullDatedMeasure, CohortRightsSerializer
from cohort.tools import get_all_cohorts_rights, get_dict_cohort_pop_source

_logger = logging.getLogger('django.request')


class NoUpdateViewSetMixin:
    def update(self, request, *args, **kwargs):
        return Response(
            {"response": "request_query_snapshot manual update not possible"},
            status=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, *args, **kwargs):
        return Response(
            {"response": "request_query_snapshot manual update not possible"},
            status=status.HTTP_400_BAD_REQUEST)


class BaseViewSet(viewsets.ModelViewSet):
    permission_classes = (IsOwner,)

    def get_serializer_context(self):
        return {'request': self.request}


class UserObjectsRestrictedViewSet(BaseViewSet):
    def get_queryset(self):
        return self.__class__.queryset.filter(owner=self.request.user)

    def create(self, request, *args, **kwargs):
        if type(request.data) == QueryDict:
            request.data._mutable = True
        request.data['owner'] = request.data.get('owner', request.user.pk)

        return super(UserObjectsRestrictedViewSet, self).create(
            request, *args, **kwargs)

    # todo : remove when front is ready
    #  (front should not post with '_id' fields)
    def initial(self, request, *args, **kwargs):
        super(UserObjectsRestrictedViewSet, self) \
            .initial(request, *args, **kwargs)

        s = self.get_serializer_class()()
        primary_key_fields = [f.field_name for f in s._writable_fields
                              if isinstance(f, RelatedField)]

        if isinstance(request.data, QueryDict):
            request.data._mutable = True

        for field_name in primary_key_fields:
            field_name_with_id = f'{field_name}_id'
            if field_name_with_id in request.data:
                request.data[field_name] = request.data[field_name_with_id]


class CohortFilter(filters.FilterSet):
    name = filters.CharFilter(field_name='name', lookup_expr="icontains")
    min_result_size = filters.NumberFilter(field_name='dated_measure__measure', lookup_expr='gte')
    max_result_size = filters.NumberFilter(field_name='dated_measure__measure', lookup_expr='lte')
    # ?min_created_at=2015-04-23
    min_fhir_datetime = filters.IsoDateTimeFilter(field_name='dated_measure__fhir_datetime', lookup_expr="gte")
    max_fhir_datetime = filters.IsoDateTimeFilter(field_name='dated_measure__fhir_datetime', lookup_expr="lte")
    request_id = filters.CharFilter(field_name='request_query_snapshot__request__pk')

    # unused, untested
    def perimeter_filter(self, queryset, field, value):
        return queryset.filter(request_query_snapshot__perimeters_ids__contains=[value])

    def perimeters_filter(self, queryset, field, value):
        return queryset.filter(request_query_snapshot__perimeters_ids__contains=value.split(","))

    def multi_value_filter(self, queryset, field, value: str):
        if value:
            sub_values = [val.strip() for val in value.split(",")]
            return queryset.filter(join_qs([Q(**{field: v}) for v in sub_values]))
        return queryset

    type = filters.AllValuesMultipleFilter()
    perimeter_id = filters.CharFilter(method="perimeter_filter")
    perimeters_ids = filters.CharFilter(method="perimeters_filter")
    fhir_group_id = filters.CharFilter(method="multi_value_filter", field_name="fhir_group_id")
    status = filters.CharFilter(method="multi_value_filter", field_name="request_job_status")

    ordering = OrderingFilter(fields=('-created_at',
                                      'modified_at',
                                      'name',
                                      ('dated_measure__measure', 'result_size'),
                                      ('dated_measure__fhir_datetime', 'fhir_datetime'),
                                      'type',
                                      'favorite',
                                      'request_job_status'))

    class Meta:
        model = CohortResult
        fields = ('name',
                  'min_result_size',
                  'max_result_size',
                  'min_fhir_datetime',
                  'max_fhir_datetime',
                  'favorite',
                  'fhir_group_id',
                  'create_task_id',
                  'request_query_snapshot',
                  'request_query_snapshot__request',
                  'request_id',
                  'request_job_status',
                  'status',
                  # unused, untested
                  'type',
                  'perimeter_id',
                  'perimeters_ids')


class CohortResultViewSet(NestedViewSetMixin, UserObjectsRestrictedViewSet):
    queryset = CohortResult.objects.select_related('request_query_snapshot__request')\
                                   .annotate(request_id=F('request_query_snapshot__request__uuid')).all()
    serializer_class = CohortResultSerializer
    http_method_names = ['get', 'post', 'patch', 'delete']
    lookup_field = "uuid"
    swagger_tags = ['Cohort - cohorts']
    pagination_class = LimitOffsetPagination
    filterset_class = CohortFilter
    search_fields = ('$name', '$description')

    def get_serializer_class(self):
        if self.request.method in ["POST", "PUT", "PATCH"] and "dated_measure" in self.request.data \
                and isinstance(self.request.data["dated_measure"], dict):
            return CohortResultSerializerFullDatedMeasure
        if self.request.method == "GET":
            return CohortResultSerializerFullDatedMeasure
        return super(CohortResultViewSet, self).get_serializer_class()

    def create(self, request, *args, **kwargs):
        if type(request.data) == QueryDict:
            request.data._mutable = True
        # todo remove possibility to post _id when Front is ready
        if 'dated_measure_id' not in request.data:
            if 'dated_measure' in request.data:
                dated_measure = request.data['dated_measure']
                if isinstance(dated_measure, dict):
                    if "request_query_snapshot" in request.data:
                        dated_measure["request_query_snapshot"] = request.data["request_query_snapshot"]
        else:
            request.data['dated_measure'] = request.data['dated_measure_id']

        return super(CohortResultViewSet, self).create(request, *args, **kwargs)

    @action(methods=['get'], detail=False, url_path='jobs/active')
    def get_active_jobs(self, request, *args, **kwargs):
        active_statuses = [JobStatus.new, JobStatus.validated, JobStatus.started, JobStatus.pending]
        jobs_count = CohortResult.objects.filter(request_job_status__in=active_statuses).count()
        if not jobs_count:
            return HttpResponse(status=status.HTTP_204_NO_CONTENT)
        return JsonResponse(data={"jobs_count": jobs_count}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        method='get',
        operation_summary="Give cohorts aggregation read patient rights, export csv rights and transfer jupyter rights."
                          "It check accesses with perimeters population source for each cohort found.",
        responses={'201': openapi.Response("give rights in caresite perimeters found", CohortRightsSerializer())})
    @action(detail=False, methods=['get'], url_path="cohort-rights")
    def get_perimeters_read_right_accesses(self, request, *args, **kwargs):
        user_accesses = get_user_valid_manual_accesses_queryset(self.request.user)

        if not user_accesses:
            raise Http404("ERROR: No Accesses found")
        if self.request.query_params:
            # Case with perimeters search params
            cohorts_filtered_by_search = self.filter_queryset(self.get_queryset())
            if not cohorts_filtered_by_search:
                raise Http404("ERROR: No Cohort Found")
            list_cohort_id = [cohort.fhir_group_id for cohort in cohorts_filtered_by_search]
            cohort_dict_pop_source = get_dict_cohort_pop_source(list_cohort_id)

            return Response(CohortRightsSerializer(get_all_cohorts_rights(user_accesses, cohort_dict_pop_source),
                                                   many=True).data)

        all_user_cohorts = CohortResult.objects.filter(owner=self.request.user)
        if not all_user_cohorts:
            return Response("WARN: You do not have any cohort")
        list_cohort_id = [cohort.fhir_group_id for cohort in all_user_cohorts]
        cohort_dict_pop_source = get_dict_cohort_pop_source(list_cohort_id)
        return Response(CohortRightsSerializer(get_all_cohorts_rights(user_accesses, cohort_dict_pop_source),
                                               many=True).data)


class NestedCohortResultViewSet(SwaggerSimpleNestedViewSetMixin,
                                CohortResultViewSet):
    def create(self, request, *args, **kwargs):
        if type(request.data) == QueryDict:
            request.data._mutable = True

        if 'request_query_snapshot' in kwargs:
            request.data["request_query_snapshot"] = \
                kwargs['request_query_snapshot']

        return super(NestedCohortResultViewSet, self).create(
            request, *args, **kwargs)


class DMFilter(filters.FilterSet):
    request_id = filters.CharFilter(field_name='request_query_snapshot__request__pk')
    ordering = OrderingFilter(fields=("-created_at", "modified_at", "result_size"))

    class Meta:
        model = DatedMeasure
        fields = ('uuid',
                  'request_query_snapshot',
                  'mode',
                  'count_task_id',
                  'request_query_snapshot__request',
                  'request_id'
                  )


class DatedMeasureViewSet(NestedViewSetMixin, UserObjectsRestrictedViewSet):
    queryset = DatedMeasure.objects.all()
    serializer_class = DatedMeasureSerializer
    http_method_names = ['get', 'post', 'patch', 'delete']
    lookup_field = "uuid"
    swagger_tags = ['Cohort - dated-measures']

    filterset_class = DMFilter
    pagination_class = LimitOffsetPagination

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if CohortResult.objects.filter(dated_measure__uuid=instance.uuid).first():
            return Response({'message': "Cannot delete a DatedMeasure bound to a CohortResult"},
                            status=status.HTTP_403_FORBIDDEN)
        return super(DatedMeasureViewSet, self).destroy(request, *args, **kwargs)

    @action(methods=['post'], detail=False, url_path='create-unique')
    def create_unique(self, request, *args, **kwargs):
        """ Demande à l'API FHIR d'annuler tous les jobs de calcul de count liés à
            une construction de Requête avant d'en créer un nouveau
        """
        if "request_query_snapshot" in kwargs:
            rqs_id = kwargs['request_query_snapshot']
        elif "request_query_snapshot_id" in request.data:
            rqs_id = request.data.get("request_query_snapshot_id")
        else:
            _logger.exception("'request_query_snapshot_id' not provided")
            return HttpResponseBadRequest()

        try:
            rqs: RequestQuerySnapshot = RequestQuerySnapshot.objects.get(pk=rqs_id)
        except RequestQuerySnapshot.DoesNotExist:
            _logger.exception("Invalid 'request_query_snapshot_id'")
            return HttpResponseBadRequest()

        dms_jobs = rqs.request.dated_measures.filter(request_job_status__in=[JobStatus.started, JobStatus.pending])\
                                             .prefetch_related('cohort', 'restricted_cohort')
        for job in dms_jobs:
            if job.cohort.all() or job.restricted_cohort.all():
                continue    # if the dated measure is bound to a cohort, don't cancel it
            job_status = job.request_job_status
            try:
                if job_status == JobStatus.started:
                    headers = get_fhir_authorization_header(request)
                    new_status = cancel_job(job.request_job_id, headers)
                else:
                    app.control.revoke(job.count_task_id)
                job.request_job_status = job_status == JobStatus.started and new_status or JobStatus.cancelled
                job.save()
            except Exception as e:
                _logger.exception(f"Error while cancelling {status} job [{job.uuid}] - {e}")
                return HttpResponseServerError()
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
            cancel_job(instance.request_job_id, get_fhir_authorization_header(request))
        except Exception as e:
            return Response(dict(message=str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class NestedDatedMeasureViewSet(SwaggerSimpleNestedViewSetMixin,
                                DatedMeasureViewSet):
    @swagger_auto_schema(auto_schema=None)
    def abort(self, request, *args, **kwargs):
        return self.abort(self, request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        if type(request.data) == QueryDict:
            request.data._mutable = True

        if 'request_query_snapshot' in kwargs:
            request.data["request_query_snapshot"] \
                = kwargs['request_query_snapshot']

        return super(NestedDatedMeasureViewSet, self).create(
            request, *args, **kwargs)


class RQSFilter(filters.FilterSet):
    ordering = OrderingFilter(fields=('-created_at', 'modified_at'))

    class Meta:
        model = RequestQuerySnapshot
        fields = ('uuid', 'request', 'is_active_branch', 'shared_by',
                  'previous_snapshot', 'request', 'request__parent_folder')


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
    filterset_class = RQSFilter
    search_fields = ('$serialized_query',)

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

    def create(self, request, *args, **kwargs):
        if type(request.data) == QueryDict:
            request.data._mutable = True

        if 'request_id' in kwargs:
            request.data["request"] = kwargs['request_id']
        if 'previous_snapshot' in kwargs:
            request.data["previous_snapshot"] = kwargs['previous_snapshot']

        return super(NestedRqsViewSet, self) \
            .create(request, *args, **kwargs)


class RequestFilter(filters.FilterSet):
    ordering = OrderingFilter(fields=('name', 'created_at', 'modified_at',
                                      'favorite', 'data_type_of_query'))

    class Meta:
        model = Request
        fields = ('uuid', 'name', 'favorite', 'data_type_of_query',
                  'parent_folder', 'shared_by')


class RequestViewSet(NestedViewSetMixin, UserObjectsRestrictedViewSet):
    queryset = Request.objects.all()
    serializer_class = RequestSerializer
    http_method_names = ["get", "post", "patch", "delete"]
    lookup_field = "uuid"
    swagger_tags = ["Cohort - requests"]

    pagination_class = LimitOffsetPagination

    filterset_class = RequestFilter
    search_fields = ("$name", "$description",)


class NestedRequestViewSet(SwaggerSimpleNestedViewSetMixin, RequestViewSet):
    def create(self, request, *args, **kwargs):
        if type(request.data) == QueryDict:
            request.data._mutable = True

        if 'parent_folder' in kwargs:
            request.data["parent_folder"] = kwargs['parent_folder']

        return super(NestedRequestViewSet, self) \
            .create(request, *args, **kwargs)


class FolderFilter(filters.FilterSet):
    ordering = OrderingFilter(fields=('name', 'created_at', 'modified_at'))

    class Meta:
        model = Folder
        fields = ['uuid', 'name']


class FolderViewSet(CustomLoggingMixin, NestedViewSetMixin, UserObjectsRestrictedViewSet):
    queryset = Folder.objects.all()
    serializer_class = FolderSerializer
    http_method_names = ['get', 'post', 'patch', 'delete']
    lookup_field = "uuid"

    swagger_tags = ['Cohort - folders']
    logging_methods = ['POST', 'PUT', 'PATCH', 'DELETE']
    pagination_class = LimitOffsetPagination

    filterset_class = FolderFilter
    search_fields = ('$name',)
