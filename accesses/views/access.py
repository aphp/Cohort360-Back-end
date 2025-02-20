import json

from django.db.models import BooleanField, When, Case, Value, QuerySet
from django.utils import timezone
from django.conf import settings

from django_filters import OrderingFilter
from django_filters import rest_framework as filters
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from accesses.services.accesses import accesses_service
from accesses.views import BaseViewSet
from admin_cohort.permissions import IsAuthenticated
from admin_cohort.tools.cache import cache_response
from admin_cohort.tools.request_log_mixin import RequestLogMixin
from accesses.models import Access
from accesses.permissions import AccessesPermission
from accesses.serializers import AccessSerializer, DataRightSerializer, ExpiringAccessesSerializer


class AccessFilter(filters.FilterSet):
    ordering = OrderingFilter(fields=('start_datetime',
                                      'end_datetime',
                                      'created_by',
                                      'updated_by',
                                      ('role__name', 'role_name'),
                                      ('perimeter__name', 'perimeter_name'),
                                      ('sql_is_valid', 'is_valid')))

    class Meta:
        model = Access
        fields = ("source",
                  "perimeter_id",
                  "role_id",
                  "profile_id",
                  "start_datetime",
                  "end_datetime")


class AccessViewSet(RequestLogMixin, BaseViewSet):
    serializer_class = AccessSerializer
    queryset = Access.objects.all()
    lookup_field = "id"
    filterset_class = AccessFilter
    permission_classes = [IsAuthenticated, AccessesPermission]
    http_method_names = ['get', 'post', 'patch', 'delete']
    logging_methods = ['POST', 'PATCH', 'DELETE']
    swagger_tags = ['Accesses']
    search_fields = ["profile__user__firstname",
                     "profile__user__lastname",
                     "profile__user__email",
                     "profile__user_id",
                     "perimeter__name"]

    def get_permissions(self):
        if self.action in (self.get_my_accesses.__name__,
                           self.get_my_data_reading_rights.__name__):
            return [IsAuthenticated()]
        return super().get_permissions()

    def get_serializer_class(self):
        if self.request.method == "GET" and "expiring" in self.request.query_params:
            return ExpiringAccessesSerializer
        return self.serializer_class

    def get_queryset(self) -> QuerySet:
        queryset = super().get_queryset()
        now = timezone.now()
        queryset = queryset.annotate(sql_is_valid=Case(When(start_datetime__lte=now, end_datetime__gte=now, then=Value(True)),
                                                       default=Value(False), output_field=BooleanField()))
        return queryset

    @extend_schema(responses={status.HTTP_200_OK: AccessSerializer},
                   parameters=[OpenApiParameter("include_parents", OpenApiTypes.BOOL)])
    @cache_response()
    def list(self, request, *args, **kwargs):
        accesses = self.filter_queryset(self.get_queryset())
        if request.query_params.get("profile_id"):
            accesses = accesses_service.filter_accesses_for_user(user=request.user,
                                                                 accesses=accesses)
        if request.query_params.get("perimeter_id"):
            accesses = accesses_service.get_accesses_on_perimeter(user=request.user,
                                                                  accesses=self.get_queryset(),
                                                                  perimeter_id=request.query_params.get("perimeter_id"),
                                                                  include_parents=json.loads(request.query_params.get("include_parents", "false")),
                                                                  include_children=json.loads(request.query_params.get("include_children", "false")))
        page = self.paginate_queryset([a for a in accesses])
        if page:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(accesses, many=True)
        return Response(data=serializer.data, status=status.HTTP_200_OK)

    @extend_schema(request=AccessSerializer,
                   responses={status.HTTP_201_CREATED: AccessSerializer})
    def create(self, request, *args, **kwargs):
        try:
            accesses_service.process_create_data(data=request.data)
        except ValueError as e:
            return Response(data={"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return super().create(request, *args, **kwargs)

    @extend_schema(request=AccessSerializer,
                   responses={status.HTTP_200_OK: AccessSerializer})
    def partial_update(self, request, *args, **kwargs):
        try:
            accesses_service.process_patch_data(access=self.get_object(), data=request.data)
        except ValueError as e:
            return Response(data={"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(request=AccessSerializer,
                   responses={status.HTTP_200_OK: AccessSerializer})
    @action(url_path="close", detail=True, methods=['patch'])
    def close(self, request, *args, **kwargs):
        now = timezone.now()
        try:
            accesses_service.check_access_closing_date(access=self.get_object(), end_datetime_now=now)
        except ValueError as e:
            return Response(data={"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        request.data.update({'end_datetime': now})
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(responses={status.HTTP_204_NO_CONTENT: None})
    def destroy(self, request, *args, **kwargs):
        access = self.get_object()
        if access.start_datetime and access.start_datetime < timezone.now():
            return Response(data={"error": "L'accès est déjà activé, il ne peut plus être supprimé."},
                            status=status.HTTP_400_BAD_REQUEST)
        self.perform_destroy(access)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(responses={status.HTTP_200_OK: AccessSerializer(many=True)})
    @action(url_path="my-accesses", methods=['get'], detail=False)
    @cache_response()
    def get_my_accesses(self, request, *args, **kwargs):
        user = request.user
        accesses = accesses_service.get_user_valid_accesses(user=user)
        expiring = json.loads(request.query_params.get("expiring", "false"))
        if expiring:
            accesses = accesses_service.get_expiring_accesses(user=user, accesses=accesses)
            if not accesses:
                return Response(data={"message": f"No accesses to expire in the next {settings.ACCESS_EXPIRY_FIRST_ALERT_IN_DAYS} days"},
                                status=status.HTTP_200_OK)
        return Response(data=self.get_serializer(accesses, many=True).data,
                        status=status.HTTP_200_OK)

    @extend_schema(responses={status.HTTP_200_OK: AccessSerializer(many=True)})
    @action(methods=['get'], url_path="my-data-rights", detail=False)
    @cache_response()
    def get_my_data_reading_rights(self, request, *args, **kwargs):
        perimeters_ids = request.query_params.get('perimeters_ids')
        data_rights = accesses_service.get_data_reading_rights(user=request.user, target_perimeters_ids=perimeters_ids)
        return Response(data=DataRightSerializer(data_rights, many=True).data,
                        status=status.HTTP_200_OK)
