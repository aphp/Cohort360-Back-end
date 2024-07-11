from django.db.models import QuerySet, F, Func, Value
from django_filters import rest_framework as filters
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

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
    swagger_tags = ['Accesses - profiles']
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

    @swagger_auto_schema(manual_parameters=list(map(lambda x: openapi.Parameter(name=x[0], in_=openapi.IN_QUERY,
                                                                                description=x[1], type=x[2],
                                                                                pattern=x[3] if len(x) == 4 else None),
                                                    [["user_id", "Search type", openapi.TYPE_STRING, r"\d{1,7}"],
                                                     ["user", "Filter type (User's id)", openapi.TYPE_STRING,
                                                      r"\d{1,7}"],
                                                     ["provider_name", "Search type", openapi.TYPE_STRING],
                                                     ["provider_id", "Search type", openapi.TYPE_STRING],
                                                     ["email", "Search type", openapi.TYPE_STRING],
                                                     ["lastname", "Search type", openapi.TYPE_STRING],
                                                     ["firstname", "Search type", openapi.TYPE_STRING],
                                                     ["id", "Filter type", openapi.TYPE_INTEGER],
                                                     ["source", "Filter type ('MANUAL', 'ORBIS', etc.)",
                                                      openapi.TYPE_STRING],
                                                     ["is_active", "Filter type", openapi.TYPE_BOOLEAN],
                                                     ["search",
                                                      f"Search on multiple fields {' - '.join(search_fields)}",
                                                      openapi.TYPE_STRING]])))
    @cache_response()
    def list(self, request, *args, **kwargs):
        return super(ProfileViewSet, self).list(request, *args, **kwargs)

    def perform_destroy(self, instance):
        instance.entry_deleted_by = self.request.user.username
        return super(ProfileViewSet, self).perform_destroy(instance)
