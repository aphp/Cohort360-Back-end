from django.db.models import Q
from django_filters import rest_framework as filters
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import AND
from rest_framework.response import Response

from admin_cohort import conf_auth
from admin_cohort.models import User
from admin_cohort.permissions import IsAuthenticated, can_user_read_users
from admin_cohort.settings import MANUAL_SOURCE
from admin_cohort.views import BaseViewset, CustomLoggingMixin
from . import swagger_metadata
from ..models import Profile
from ..permissions import ProfilePermissions, HasUserAddingPermission
from ..serializers import ProfileSerializer, ReducedProfileSerializer, ProfileCheckSerializer


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
    logging_methods = ['POST', 'PUT', 'PATCH', 'DELETE']
    permission_classes = [lambda: AND(IsAuthenticated(), ProfilePermissions())]
    swagger_tags = ['Accesses - profiles']
    filterset_class = ProfileFilter
    search_fields = ["lastname", "firstname", "email", "user_id"]

    def get_serializer_class(self):
        if self.request.method == 'GET' and not can_user_read_users(self.request.user):
            return ReducedProfileSerializer
        return ProfileSerializer

    @swagger_auto_schema(manual_parameters=swagger_metadata.profile_list_manual_parameters)
    def list(self, request, *args, **kwargs):
        return super(ProfileViewSet, self).list(request, *args, **kwargs)

    @swagger_auto_schema(request_body=swagger_metadata.profile_partial_update_request_body)
    def partial_update(self, request, *args, **kwargs):
        return super(ProfileViewSet, self).partial_update(request, *args, **kwargs)

    @swagger_auto_schema(auto_schema=None)
    def update(self, request, *args, **kwargs):
        return super(ProfileViewSet, self).update(request, *args, **kwargs)

    @swagger_auto_schema(request_body=swagger_metadata.profile_create_request_body)
    def create(self, request, *args, **kwargs):
        return super(ProfileViewSet, self).create(request, *args, **kwargs)

    def perform_destroy(self, instance):
        instance.entry_deleted_by = self.request.user.provider_username
        return super(ProfileViewSet, self).perform_destroy(instance)

    @swagger_auto_schema(request_body=swagger_metadata.check_existing_user_request_body,
                         responses=swagger_metadata.check_existing_user_responses)
    @action(url_path="check", detail=False, methods=['post'], permission_classes=(HasUserAddingPermission,))
    def check_existing_user(self, request, *args, **kwargs):
        from admin_cohort.serializers import UserSerializer

        psv = self.request.data.get("user_id", self.request.data.get("provider_source_value", None))
        if not psv:
            return Response("No provider_source_value provided", status=status.HTTP_400_BAD_REQUEST)
        person = conf_auth.check_id_aph(psv)
        if person is not None:
            manual_profile: Profile = Profile.objects.filter(Profile.Q_is_valid()
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
