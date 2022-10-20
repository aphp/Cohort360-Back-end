from django.db.models import Q
from django_filters import rest_framework as filters
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import AND
from rest_framework.response import Response

from admin_cohort.settings import MANUAL_SOURCE
from ..models import Profile
from ..permissions import ProfilePermissions, HasUserAddingPermission
from ..serializers import ProfileSerializer, ReducedProfileSerializer, \
    ProfileCheckSerializer
from admin_cohort import conf_auth
from admin_cohort.permissions import IsAuthenticated, can_user_read_users
from admin_cohort.views import BaseViewset, CustomLoggingMixin
from admin_cohort.models import User


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
        fields = (
            "provider_id",
            "source", "cdm_source",
            "user", "provider_source_value",
            "provider_name",
            "lastname",
            "firstname",
            "email",
            "provider_history_id", "id",
            "is_active"
        )


class ProfileViewSet(CustomLoggingMixin, BaseViewset):
    queryset = Profile.objects.filter(delete_datetime__isnull=True).all()
    lookup_field = "id"
    logging_methods = ['POST', 'PUT', 'PATCH', 'DELETE']
    permission_classes = [
        lambda: AND(IsAuthenticated(), ProfilePermissions()),
    ]

    swagger_tags = ['Accesses - profiles']
    filterset_class = ProfileFilter
    search_fields = ["lastname", "firstname", "email", "user_id"]

    def get_serializer_class(self):
        return (
            ReducedProfileSerializer
            if (self.request.method == 'GET'
                and not can_user_read_users(self.request.user))
            else ProfileSerializer)

    @swagger_auto_schema(
        manual_parameters=list(map(
            lambda x: openapi.Parameter(
                name=x[0], in_=openapi.IN_QUERY, description=x[1], type=x[2],
                pattern=x[3] if len(x) == 4 else None),
            [
                ["provider_source_value",
                 "(to deprecate -> user) Search type",
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
                ["provider_id", "Filter type", openapi.TYPE_INTEGER],
                ["cdm_source",
                 "(to deprecate -> source) Filter type "
                 "('MANUAL', 'ORBIS', etc.)",
                 openapi.TYPE_STRING],
                ["source", "Filter type ('MANUAL', 'ORBIS', etc.)",
                 openapi.TYPE_STRING],
                ["is_active", "Filter type", openapi.TYPE_BOOLEAN],
                [
                    "search",
                    "Filter on several fields (provider_source_value, "
                    "provider_name, lastname, firstname, email)",
                    openapi.TYPE_STRING
                ],
            ])))
    def list(self, request, *args, **kwargs):
        return super(ProfileViewSet, self).list(request, *args, **kwargs)

    @swagger_auto_schema(request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            "firstname": openapi.Schema(type=openapi.TYPE_STRING),
            "lastname": openapi.Schema(type=openapi.TYPE_STRING),
            "email": openapi.Schema(type=openapi.TYPE_STRING),
            "is_active": openapi.Schema(type=openapi.TYPE_BOOLEAN),
        }))
    def partial_update(self, request, *args, **kwargs):
        return super(ProfileViewSet, self) \
            .partial_update(request, *args, **kwargs)

    @swagger_auto_schema(auto_schema=None)
    def update(self, request, *args, **kwargs):
        return super(ProfileViewSet, self).update(request, *args, **kwargs)

    @swagger_auto_schema(request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            "firstname": openapi.Schema(type=openapi.TYPE_STRING),
            "lastname": openapi.Schema(type=openapi.TYPE_STRING),
            "email": openapi.Schema(type=openapi.TYPE_STRING),
            "provider_id": openapi.Schema(type=openapi.TYPE_INTEGER,
                                          description="(to deprecate)"),
            "user": openapi.Schema(type=openapi.TYPE_STRING),
            "provider_source_value": openapi.Schema(
                type=openapi.TYPE_STRING, description="(to deprecate)"),
        }))
    def create(self, request, *args, **kwargs):
        return super(ProfileViewSet, self).create(request, *args, **kwargs)

    def perform_destroy(self, instance):
        instance.entry_deleted_by = self.request.user.provider_username
        return super(ProfileViewSet, self).perform_destroy(instance)

    @swagger_auto_schema(request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            "provider_source_value": openapi.Schema(
                type=openapi.TYPE_STRING,
                description="(to deprecate, user 'user_id' instead)"),
            "user_id": openapi.Schema(type=openapi.TYPE_STRING),
        }
    ), responses={
        '201': openapi.Response("User found", ProfileCheckSerializer()),
        '204': openapi.Response("No user found")
    })
    @action(
        detail=False, methods=['post'],
        permission_classes=(HasUserAddingPermission,), url_path="check"
    )
    def check_existing_user(self, request, *args, **kwargs):
        from admin_cohort.serializers import UserSerializer

        psv = self.request.data.get("user_id", self.request.data.get("provider_source_value", None))
        if not psv:
            return Response("No provider_source_value provided", status=status.HTTP_400_BAD_REQUEST)
        person = conf_auth.check_id_aph(psv)
        if person is not None:
            manual_profile: Profile = Profile.objects.filter(Profile.Q_is_valid()
                                                             # & Q(user=person) # /!\ User instance != IdResp instance
                                                             & Q(user__provider_username=person.user_id)
                                                             & Q(source=MANUAL_SOURCE)
                                                             ).first()

            user: User = User.objects.filter(provider_username=person.user_id).first()
            u_data = UserSerializer(user).data if user else None

            data = ProfileCheckSerializer({"firstname": person.firstname,
                                           "lastname": person.lastname,
                                           "user_id": person.user_id,
                                           "email": person.email,
                                           "provider": u_data,
                                           "user": u_data,
                                           "manual_profile": manual_profile
                                           }).data
            return Response(data, status=status.HTTP_200_OK, headers=self.get_success_headers(data))
        return Response(status=status.HTTP_204_NO_CONTENT)
