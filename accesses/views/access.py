import json

from django.db.models import BooleanField, When, Case, Value, QuerySet
from django.utils import timezone
from django_filters import OrderingFilter
from django_filters import rest_framework as filters
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from accesses.services.access import accesses_service
from admin_cohort.permissions import IsAuthenticated
from admin_cohort.settings import ACCESS_EXPIRY_FIRST_ALERT_IN_DAYS
from admin_cohort.tools.cache import cache_response
from admin_cohort.views import BaseViewSet, CustomLoggingMixin
from accesses.models import Access
from accesses.permissions import AccessesPermission
from accesses.serializers import AccessSerializer, DataRightSerializer, ExpiringAccessesSerializer


class AccessFilter(filters.FilterSet):
    profile_id = filters.CharFilter(field_name="profile_id")
    ordering = OrderingFilter(fields=('start_datetime',
                                      'end_datetime',
                                      'created_by',
                                      'updated_by',
                                      ('role__name', 'role_name'),
                                      ('perimeter__name', 'perimeter_name'),
                                      ('sql_is_valid', 'is_valid')))

    class Meta:
        model = Access
        fields = "__all__"


class AccessViewSet(CustomLoggingMixin, BaseViewSet):
    serializer_class = AccessSerializer
    queryset = Access.objects.all()
    lookup_field = "id"
    filterset_class = AccessFilter
    permission_classes = [IsAuthenticated, AccessesPermission]
    http_method_names = ['get', 'post', 'patch', 'delete']
    logging_methods = ['POST', 'PATCH', 'DELETE']
    swagger_tags = ['Accesses - accesses']
    search_fields = ["profile__firstname",
                     "profile__lastname",
                     "profile__email",
                     "profile__user_id",
                     "perimeter__name"]

    def get_permissions(self):
        if self.action in ("get_my_accesses", "get_my_data_reading_rights"):
            return [IsAuthenticated()]
        return super().get_permissions()

    def get_serializer_class(self):
        if self.request.method == "GET" and "expiring" in self.request.query_params:
            return ExpiringAccessesSerializer
        return self.serializer_class

    def get_queryset(self) -> QuerySet:
        queryset = super(AccessViewSet, self).get_queryset()
        now = timezone.now()
        queryset = queryset.annotate(sql_is_valid=Case(When(start_datetime__lte=now, end_datetime__gte=now, then=Value(True)),
                                                       default=Value(False), output_field=BooleanField()))
        return queryset

    @swagger_auto_schema(manual_parameters=list(map(lambda x: openapi.Parameter(in_=openapi.IN_QUERY, name=x[0], description=x[1], type=x[2]),
                                                    [["user_id", "Search type", openapi.TYPE_STRING],
                                                     ["perimeter_id", "Filter type", openapi.TYPE_STRING],
                                                     ["include_parents", "Filter type", openapi.TYPE_BOOLEAN],
                                                     ["search", f"Will search in multiple fields: {','.join(search_fields)}", openapi.TYPE_STRING],
                                                     ["ordering", "Order by role_name, start_datetime, end_datetime, is_valid. Prepend '-' for "
                                                                  "descending order", openapi.TYPE_STRING]])))
    # @cache_response()
    def list(self, request, *args, **kwargs):
        accesses = self.filter_queryset(self.get_queryset())
        if request.query_params.get("profile_id"):
            accesses = accesses_service.filter_accesses_for_user(user=request.user,
                                                                 accesses=accesses)
        if request.query_params.get("perimeter_id"):
            accesses = accesses_service.get_accesses_on_perimeter(user=request.user,
                                                                  accesses=accesses,
                                                                  perimeter_id=request.query_params.get("perimeter_id"),
                                                                  include_parents=json.loads(request.query_params.get("include_parents", "false")))
        page = self.paginate_queryset(accesses)
        if page:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(accesses, many=True)
        return Response(data=serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={"profile_id": openapi.Schema(type=openapi.TYPE_INTEGER),
                    "perimeter_id": openapi.Schema(type=openapi.TYPE_INTEGER),
                    "role_id": openapi.Schema(type=openapi.TYPE_INTEGER),
                    "start_datetime": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME,
                                                     description="Doit être dans le futur.\nSi vide ou null, sera défini à now().\nDoit contenir "
                                                                 "la timezone ou bien sera considéré comme UTC."),
                    "end_datetime": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME,
                                                   description="Doit être dans le futur. \nSi vide ou null, sera défini à start_datetime +2 "
                                                               "ans.\nDoit contenir la timezone ou bien sera considéré comme UTC.")},
        required=['profile_id', 'perimeter_id', 'role_id']))
    def create(self, request, *args, **kwargs):
        try:
            accesses_service.process_create_data(data=request.data)
        except ValueError as e:
            return Response(data=str(e), status=status.HTTP_400_BAD_REQUEST)
        return super(AccessViewSet, self).create(request, *args, **kwargs)

    @swagger_auto_schema(request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={"start_datetime": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME,
                                                     description="Doit être dans le futur.\nNe peut pas être modifié "
                                                                 "si start_datetime actuel est déja passé.\nSera mis à "
                                                                 "now() si null.\nDoit contenir la timezone ou bien "
                                                                 "sera considéré comme UTC."),
                    "end_datetime": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME,
                                                   description="Doit être dans le futur.\nNe peut pas être modifié si "
                                                               "end_datetime actuel est déja passé.\nNe peut pas être "
                                                               "mise à null.\nDoit contenir la timezone ou bien sera "
                                                               "considéré comme UTC.")}))
    def partial_update(self, request, *args, **kwargs):
        try:
            accesses_service.process_patch_data(access=self.get_object(), data=request.data)
        except ValueError as e:
            return Response(data=str(e), status=status.HTTP_400_BAD_REQUEST)
        return super(AccessViewSet, self).partial_update(request, *args, **kwargs)

    @swagger_auto_schema(method="PATCH", operation_summary="Will set end_datetime to now, to close the access.")
    @action(url_path="close", detail=True, methods=['patch'])
    def close(self, request, *args, **kwargs):
        now = timezone.now()
        try:
            accesses_service.check_access_closing_date(access=self.get_object(), end_datetime_now=now)
        except ValueError as e:
            return Response(data=str(e), status=status.HTTP_400_BAD_REQUEST)
        request.data.update({'end_datetime': now})
        return super(AccessViewSet, self).partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        access = self.get_object()
        if access.start_datetime and access.start_datetime < timezone.now():
            return Response(data="L'accès est déjà activé, il ne peut plus être supprimé.",
                            status=status.HTTP_400_BAD_REQUEST)
        self.perform_destroy(access)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(operation_summary="Get the authenticated user's valid accesses.",
                         manual_parameters=[openapi.Parameter(name="expiring", description="Filter accesses to expire soon",
                                                              in_=openapi.IN_QUERY, type=openapi.TYPE_BOOLEAN)],
                         responses={200: openapi.Response('All valid accesses or ones to expire soon', AccessSerializer)})
    @action(url_path="my-accesses", methods=['get'], detail=False)
    @cache_response()
    def get_my_accesses(self, request, *args, **kwargs):
        user = request.user
        accesses = accesses_service.get_user_valid_accesses(user=user)
        if request.query_params.get("expiring"):
            accesses = accesses_service.get_expiring_accesses(user=user, accesses=accesses)
            if not accesses:
                return Response(data={"message": f"No accesses to expire in the next {ACCESS_EXPIRY_FIRST_ALERT_IN_DAYS} days"},
                                status=status.HTTP_200_OK)
        return Response(data=self.get_serializer(accesses, many=True).data,
                        status=status.HTTP_200_OK)

    @swagger_auto_schema(operation_description="Returns the list of rights allowing to read patients data on given perimeters.",
                         manual_parameters=[i for i in map(lambda x: openapi.Parameter(in_=openapi.IN_QUERY, name=x[0], description=x[1],
                                                                                       type=x[2], pattern=x[3] if len(x) == 4 else None),
                                                           [["perimeters_ids", "Perimeters IDs on which compute data rights, separated by ','",
                                                             openapi.TYPE_STRING]])],
                         responses={200: openapi.Response('Data Reading Rights computed per perimeter', DataRightSerializer)})
    @action(methods=['get'], url_path="my-data-rights", detail=False)
    @cache_response()
    def get_my_data_reading_rights(self, request, *args, **kwargs):
        perimeters_ids = request.query_params.get('perimeters_ids')
        data_rights = accesses_service.get_data_reading_rights(user=request.user, target_perimeters_ids=perimeters_ids)
        return Response(data=DataRightSerializer(data_rights, many=True).data,
                        status=status.HTTP_200_OK)
