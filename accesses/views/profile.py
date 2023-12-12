import logging

import environ
from django_filters import rest_framework as filters
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from admin_cohort.tools.cache import cache_response
from admin_cohort.permissions import IsAuthenticated, can_user_read_users
from admin_cohort.tools.request_log_mixin import RequestLogMixin
from admin_cohort.types import MissingDataError, ServerError
from admin_cohort.views import BaseViewSet
from ..models import Profile
from ..permissions import ProfilesPermission
from ..serializers import ProfileSerializer, ReducedProfileSerializer, ProfileCheckSerializer
from ..services.profiles import profiles_service

env = environ.Env()

_logger = logging.getLogger("django.request")

USERNAME_REGEX = env("USERNAME_REGEX")


class ProfileFilter(filters.FilterSet):
    provider_name = filters.CharFilter(lookup_expr="icontains")
    lastname = filters.CharFilter(lookup_expr="icontains")
    firstname = filters.CharFilter(lookup_expr="icontains")
    email = filters.CharFilter(lookup_expr="icontains")
    provider_history_id = filters.NumberFilter(field_name='id')

    class Meta:
        model = Profile
        fields = ("provider_id",
                  "source",
                  "user",
                  "user_id",
                  "provider_name",
                  "lastname",
                  "firstname",
                  "email",
                  "provider_history_id",
                  "id",
                  "is_active")


class ProfileViewSet(RequestLogMixin, BaseViewSet):
    queryset = Profile.objects.filter(delete_datetime__isnull=True).all()
    lookup_field = "id"
    http_method_names = ['get', 'post', 'patch', 'delete']
    logging_methods = ['POST', 'PATCH', 'DELETE']
    permission_classes = (IsAuthenticated, ProfilesPermission)
    swagger_tags = ['Accesses - profiles']
    filterset_class = ProfileFilter
    search_fields = ["lastname", "firstname", "email", "user_id"]

    def get_serializer_class(self):
        if self.request.method == 'GET' and not can_user_read_users(self.request.user):
            return ReducedProfileSerializer
        return ProfileSerializer

    @swagger_auto_schema(manual_parameters=list(map(lambda x: openapi.Parameter(name=x[0], in_=openapi.IN_QUERY,
                                                                                description=x[1], type=x[2],
                                                                                pattern=x[3] if len(x) == 4 else None),
                                                    [["provider_source_value", "(to deprecate -> user) Search type",
                                                      openapi.TYPE_STRING, r"\d{1,7}"],
                                                     ["user", "Filter type (User's id)", openapi.TYPE_STRING,
                                                      r"\d{1,7}"],
                                                     ["provider_name", "Search type", openapi.TYPE_STRING],
                                                     ["email", "Search type", openapi.TYPE_STRING],
                                                     ["lastname", "Search type", openapi.TYPE_STRING],
                                                     ["firstname", "Search type", openapi.TYPE_STRING],
                                                     ["provider_history_id", "(to deprecate -> id) Filter type",
                                                      openapi.TYPE_INTEGER],
                                                     ["id", "Filter type", openapi.TYPE_INTEGER],
                                                     ["provider_id", "Filter type", openapi.TYPE_STRING],
                                                     ["source", "Filter type ('MANUAL', 'ORBIS', etc.)",
                                                      openapi.TYPE_STRING],
                                                     ["is_active", "Filter type", openapi.TYPE_BOOLEAN],
                                                     ["search", "Filter on several fields (provider_source_value, "
                                                                "provider_name, lastname, firstname, email)",
                                                      openapi.TYPE_STRING]])))
    @cache_response()
    def list(self, request, *args, **kwargs):
        return super(ProfileViewSet, self).list(request, *args, **kwargs)

    @swagger_auto_schema(request_body=openapi.Schema(type=openapi.TYPE_OBJECT,
                                                     properties={"firstname": openapi.Schema(type=openapi.TYPE_STRING),
                                                                 "lastname": openapi.Schema(type=openapi.TYPE_STRING),
                                                                 "email": openapi.Schema(type=openapi.TYPE_STRING),
                                                                 "is_active": openapi.Schema(type=openapi.TYPE_BOOLEAN)}))
    def partial_update(self, request, *args, **kwargs):
        profiles_service.process_patch_data(data=request.data)
        return super(ProfileViewSet, self).partial_update(request, *args, **kwargs)

    @swagger_auto_schema(request_body=openapi.Schema(type=openapi.TYPE_OBJECT,
                                                     properties={"firstname": openapi.Schema(type=openapi.TYPE_STRING),
                                                                 "lastname": openapi.Schema(type=openapi.TYPE_STRING),
                                                                 "email": openapi.Schema(type=openapi.TYPE_STRING),
                                                                 "provider_id": openapi.Schema(type=openapi.TYPE_STRING),
                                                                 "user": openapi.Schema(type=openapi.TYPE_STRING),
                                                                 "provider_source_value": openapi.Schema(type=openapi.TYPE_STRING)}))
    def create(self, request, *args, **kwargs):
        profiles_service.process_creation_data(data=request.data)
        return super(ProfileViewSet, self).create(request, *args, **kwargs)

    def perform_destroy(self, instance):
        instance.entry_deleted_by = self.request.user.provider_username
        return super(ProfileViewSet, self).perform_destroy(instance)

    @swagger_auto_schema(request_body=openapi.Schema(type=openapi.TYPE_OBJECT,
                                                     properties={"username": openapi.Schema(type=openapi.TYPE_STRING)}),
                         responses={'200': openapi.Response("Profile found", ProfileCheckSerializer()),
                                    '204': openapi.Response("No user found matching the given username"),
                                    '400': openapi.Response("Bad request"),
                                    '500': openapi.Response("Server error")})
    @action(detail=False, methods=['post'], url_path="check")
    def check_existing_profile(self, request, *args, **kwargs):
        try:
            res = profiles_service.check_existing_profile(username=request.data.get("username"))
            return Response(data=ProfileCheckSerializer(res).data, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response(data=f"{e}", status=status.HTTP_400_BAD_REQUEST)
        except ServerError as e:
            return Response(data=f"{e}", status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except MissingDataError as e:
            return Response(data=f"User not found - {e}", status=status.HTTP_204_NO_CONTENT)


