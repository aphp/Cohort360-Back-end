import logging
import re

import environ
from django.db.models import Q
from django_filters import rest_framework as filters
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from admin_cohort.auth.utils import check_id_aph
from admin_cohort.tools.cache import cache_response
from admin_cohort.models import User
from admin_cohort.permissions import IsAuthenticated, can_user_read_users
from admin_cohort.serializers import UserSerializer
from admin_cohort.settings import MANUAL_SOURCE
from admin_cohort.types import ServerError, MissingDataError
from admin_cohort.views import BaseViewset, CustomLoggingMixin
from ..models import Profile
from ..models.tools import q_is_valid_profile
from ..permissions import ProfilePermissions
from ..serializers import ProfileSerializer, ReducedProfileSerializer, \
    ProfileCheckSerializer

env = environ.Env()

_logger = logging.getLogger("django.request")

USERNAME_REGEX = env("USERNAME_REGEX")


class ProfileFilter(filters.FilterSet):
    provider_source_value = filters.CharFilter(field_name="user")
    provider_name = filters.CharFilter(lookup_expr="icontains")
    lastname = filters.CharFilter(lookup_expr="icontains")
    firstname = filters.CharFilter(lookup_expr="icontains")
    email = filters.CharFilter(lookup_expr="icontains")
    provider_history_id = filters.NumberFilter(field_name='id')
    cdm_source = filters.CharFilter(field_name='source')

    class Meta:
        model = Profile
        fields = ("provider_id",
                  "source", "cdm_source",
                  "user", "provider_source_value",
                  "provider_name",
                  "lastname", "firstname",
                  "email", "provider_history_id",
                  "id", "is_active")


class ProfileViewSet(CustomLoggingMixin, BaseViewset):
    queryset = Profile.objects.filter(delete_datetime__isnull=True).all()
    lookup_field = "id"
    logging_methods = ['POST', 'PATCH', 'DELETE']
    permission_classes = (IsAuthenticated, ProfilePermissions)
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
                                                     ["cdm_source", "(to deprecate -> source) Filter type "
                                                                    "('MANUAL', 'ORBIS', etc.)", openapi.TYPE_STRING],
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
        return super(ProfileViewSet, self).partial_update(request, *args, **kwargs)

    @swagger_auto_schema(request_body=openapi.Schema(type=openapi.TYPE_OBJECT,
                                                     properties={"firstname": openapi.Schema(type=openapi.TYPE_STRING),
                                                                 "lastname": openapi.Schema(type=openapi.TYPE_STRING),
                                                                 "email": openapi.Schema(type=openapi.TYPE_STRING),
                                                                 "provider_id": openapi.Schema(type=openapi.TYPE_STRING),
                                                                 "user": openapi.Schema(type=openapi.TYPE_STRING),
                                                                 "provider_source_value": openapi.Schema(type=openapi.TYPE_STRING)}))
    def create(self, request, *args, **kwargs):
        return super(ProfileViewSet, self).create(request, *args, **kwargs)

    def perform_destroy(self, instance):
        instance.entry_deleted_by = self.request.user.provider_username
        return super(ProfileViewSet, self).perform_destroy(instance)

    @swagger_auto_schema(request_body=openapi.Schema(type=openapi.TYPE_OBJECT,
                                                     properties={"username": openapi.Schema(type=openapi.TYPE_STRING)}),
                         responses={'201': openapi.Response("Profile found", ProfileCheckSerializer()),
                                    '204': openapi.Response("No profile found")})
    @action(detail=False, methods=['post'], url_path="check")
    def check_existing_profile(self, request, *args, **kwargs):
        username = request.data.get("username")
        if not username:
            return Response(data="No `username` was provided", status=status.HTTP_400_BAD_REQUEST)
        username_regex = re.compile(USERNAME_REGEX)
        if not username_regex.match(username):
            return Response(data="The given username format is not allowed", status=status.HTTP_200_OK)

        try:
            person = check_id_aph(username)
            manual_profile: Profile = Profile.objects.filter(q_is_valid_profile()
                                                             & Q(source=MANUAL_SOURCE)
                                                             & Q(user__provider_username=person.user_id)
                                                             ).first()

            user: User = User.objects.filter(provider_username=person.user_id).first()
            user_data = user and UserSerializer(user).data or None

            data = ProfileCheckSerializer({"firstname": person.firstname,
                                           "lastname": person.lastname,
                                           "user_id": person.user_id,
                                           "email": person.email,
                                           "provider": user_data,
                                           "user": user_data,
                                           "manual_profile": manual_profile
                                           }).data
            return Response(data=data, status=status.HTTP_200_OK)
        except (ServerError, MissingDataError) as e:
            _logger.error(f"Error checking username validity, username: {username}: {e}")
            return Response(data="User not found", status=status.HTTP_204_NO_CONTENT)
