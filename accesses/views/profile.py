from django.db.models import QuerySet, F, Func, Value
from django_filters import rest_framework as filters
from drf_spectacular.utils import extend_schema
from rest_framework import status

from admin_cohort.permissions import IsAuthenticated, can_user_read_users
from admin_cohort.tools.cache import cache_response
from admin_cohort.tools.request_log_mixin import RequestLogMixin
from admin_cohort.views import BaseViewSet
from accesses.models import Profile
from accesses.permissions import ProfilesPermission
from accesses.serializers import ProfileSerializer, ReducedProfileSerializer


class ProfileFilter(filters.FilterSet):
    lastname = filters.CharFilter(field_name="user.lastname", lookup_expr="icontains")
    firstname = filters.CharFilter(field_name="user.firstname", lookup_expr="icontains")
    email = filters.CharFilter(field_name="user.email", lookup_expr="icontains")
    provider_history_id = filters.NumberFilter(field_name='id')
    provider_id = filters.CharFilter(field_name="sql_provider_id", lookup_expr="icontains")
    provider_name = filters.CharFilter(field_name="sql_provider_name", lookup_expr="icontains")

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
    http_method_names = ['get', 'delete']
    logging_methods = ['DELETE']
    permission_classes = (IsAuthenticated, ProfilesPermission)
    swagger_tags = ['Profiles']
    filterset_class = ProfileFilter
    search_fields = ["lastname", "firstname", "email", "user_id"]

    def get_queryset(self) -> QuerySet:
        queryset = super().get_queryset()
        queryset = queryset.annotate(sql_provider_id=F("user__username"),
                                     sql_provider_name=Func(F('user__firstname'), Value(' '), F('user__lastname'),
                                                            function='CONCAT'))
        return queryset

    def get_serializer_class(self):
        if self.request.method == 'GET' and not can_user_read_users(self.request.user):
            return ReducedProfileSerializer
        return ProfileSerializer

    @extend_schema(tags=swagger_tags,
                   responses={status.HTTP_200_OK: ProfileSerializer})
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(tags=swagger_tags,
                   responses={status.HTTP_200_OK: ProfileSerializer})
    @cache_response()
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(tags=swagger_tags,
                   responses={status.HTTP_204_NO_CONTENT: None})
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    def perform_destroy(self, instance):
        instance.entry_deleted_by = self.request.user.username
        return super().perform_destroy(instance)
