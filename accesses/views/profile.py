from django.db.models import QuerySet, F, Func, Value
from drf_spectacular.utils import extend_schema
from rest_framework import status

from accesses.views import BaseViewSet
from admin_cohort.permissions import IsAuthenticated, can_user_read_users
from admin_cohort.tools.cache import cache_response
from admin_cohort.tools.request_log_mixin import RequestLogMixin
from accesses.models import Profile
from accesses.permissions import ProfilesPermission
from accesses.serializers import ProfileSerializer, ReducedProfileSerializer


class ProfileViewSet(RequestLogMixin, BaseViewSet):
    queryset = Profile.objects.filter(delete_datetime__isnull=True).all()
    lookup_field = "id"
    http_method_names = ['get']
    permission_classes = (IsAuthenticated, ProfilesPermission)
    swagger_tags = ['Profiles']
    filterset_fields = ("user_id",)
    search_fields = ["user__firstname", "user__lastname", "user__username"]

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

    @extend_schema(responses={status.HTTP_200_OK: ProfileSerializer(many=True)})
    @cache_response()
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(exclude=True)
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)
