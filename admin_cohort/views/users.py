import json
import logging
import re

from django.http import Http404
from django.utils import timezone
from django.conf import settings
from django_filters import rest_framework as filters, OrderingFilter
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from admin_cohort.models import User
from admin_cohort.permissions import UsersPermission
from admin_cohort.serializers import UserSerializer, UserCheckSerializer
from admin_cohort.services.users import users_service
from admin_cohort.tools.cache import cache_response
from admin_cohort.exceptions import ServerError

_logger = logging.getLogger('django.request')


class UserFilter(filters.FilterSet):
    username = filters.CharFilter(field_name='username', lookup_expr='icontains')
    firstname = filters.CharFilter(field_name='firstname', lookup_expr='icontains')
    lastname = filters.CharFilter(field_name='lastname', lookup_expr='icontains')
    email = filters.CharFilter(field_name='email', lookup_expr='icontains')
    ordering = OrderingFilter(fields=('firstname', "lastname", "username", "email"))

    class Meta:
        model = User
        fields = ['firstname', "lastname", "username", "email"]


extended_schema = extend_schema(tags=["Users"])


@extend_schema_view(
    list=extended_schema,
    retrieve=extended_schema,
    create=extended_schema,
    partial_update=extended_schema,
    check_user_exists=extended_schema,
)
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    lookup_field = "username"
    filterset_class = UserFilter
    search_fields = UserFilter.Meta.fields
    permission_classes = (UsersPermission,)
    http_method_names = ["post", "get", "patch"]

    def get_serializer_context(self):
        return {'request': self.request}

    def get_queryset(self):
        # todo : to test manual_only
        manual_only = json.loads(self.request.GET.get("manual_only", "false"))
        with_access = json.loads(self.request.GET.get("with_access", "false"))
        base_results = super().get_queryset()
        if manual_only:
            base_results = base_results.filter(profiles__source='Manual')
        if with_access:
            now = timezone.now()
            base_results = base_results.filter(
                profiles__is_active=True,
                profiles__accesses__start_datetime__lte=now,
                profiles__accesses__end_datetime__gte=now
            )
        return base_results.distinct()

    @extend_schema(responses={status.HTTP_201_CREATED: UserSerializer})
    def create(self, request, *args, **kwargs):
        users_service.validate_user_data(data=request.data)
        response = super().create(request, *args, **kwargs)
        users_service.setup_profile(data=request.data)
        return response

    @cache_response()
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(responses={status.HTTP_200_OK: UserSerializer})
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(responses={status.HTTP_200_OK: UserCheckSerializer})
    @action(detail=True, methods=['get'], url_path="check")
    def check_user_exists(self, request, *args, **kwargs):
        user, exists, found = None, False, False
        try:
            user = self.get_object().__dict__
            exists = True
        except Http404:
            username = kwargs[self.lookup_field]
            if not (username and re.compile(settings.USERNAME_REGEX).match(username)):
                return Response(data={"message": "Invalid username format"}, status=status.HTTP_400_BAD_REQUEST)
            try:
                user = users_service.try_hooks(username=username)
                found = user is not None
            except ServerError as e:
                return Response(data={"message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        if user is not None:
            res = {"username": user["username"],
                   "firstname": user["firstname"],
                   "lastname": user["lastname"],
                   "email": user["email"],
                   "already_exists": exists,
                   "found": found}
            return Response(data=UserCheckSerializer(res).data, status=status.HTTP_200_OK)
        return Response(data={"message": "User not found"}, status=status.HTTP_404_NOT_FOUND)
