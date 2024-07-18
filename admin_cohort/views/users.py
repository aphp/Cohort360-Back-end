from django.http import Http404
from django_filters import rest_framework as filters, OrderingFilter
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from admin_cohort.models import User
from admin_cohort.permissions import UsersPermission
from admin_cohort.serializers import UserSerializer, UserCheckSerializer
from admin_cohort.services.users import users_service
from admin_cohort.tools.cache import cache_response
from admin_cohort.types import ServerError
from admin_cohort.views import BaseViewSet


class UserFilter(filters.FilterSet):
    username = filters.CharFilter(field_name='username', lookup_expr='icontains')
    firstname = filters.CharFilter(field_name='firstname', lookup_expr='icontains')
    lastname = filters.CharFilter(field_name='lastname', lookup_expr='icontains')
    email = filters.CharFilter(field_name='email', lookup_expr='icontains')
    ordering = OrderingFilter(fields=('firstname', "lastname", "username", "email"))

    class Meta:
        model = User
        fields = ['firstname', "lastname", "username", "email"]


class UserViewSet(BaseViewSet):
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
        manual_only = self.request.GET.get("manual_only")
        if not manual_only:
            return super().get_queryset()
        return User.objects.filter(profiles__source='Manual').distinct()

    @swagger_auto_schema(operation_summary="Create a User and an initial Profile",
                         request_body=openapi.Schema(
                             type=openapi.TYPE_OBJECT,
                             properties={"username": openapi.Schema(type=openapi.TYPE_STRING),
                                         "firstname": openapi.Schema(type=openapi.TYPE_STRING),
                                         "lastname": openapi.Schema(type=openapi.TYPE_STRING),
                                         "email": openapi.Schema(type=openapi.TYPE_STRING)}),
                         responses={'201': openapi.Response("User created successfully"),
                                    '400': openapi.Response("Bad Request")})
    def create(self, request, *args, **kwargs):
        users_service.validate_user_data(data=request.data)
        response = super().create(request, *args, **kwargs)
        users_service.create_initial_profile(data=request.data)
        return response

    @swagger_auto_schema(manual_parameters=list(map(lambda x: openapi.Parameter(name=x[0], in_=openapi.IN_QUERY,
                                                                                description=x[1], type=x[2],
                                                                                pattern=x[3] if len(x) == 4 else None),
                                                    [["manual_only", "If True, only return users with a `manual` profile", openapi.TYPE_BOOLEAN],
                                                     ["firstname", "Filter type", openapi.TYPE_STRING],
                                                     ["lastname", "Filter type", openapi.TYPE_STRING],
                                                     ["username", "Filter type", openapi.TYPE_STRING],
                                                     ["email", "Filter type", openapi.TYPE_STRING],
                                                     ["ordering", f"Sort by one of {search_fields}", openapi.TYPE_STRING],
                                                     ["search", f"Search in multiple fields {search_fields}", openapi.TYPE_STRING],
                                                     ["page", "A page number within the paginated result set.", openapi.TYPE_INTEGER]])))
    @cache_response()
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(request_body=openapi.Schema(type=openapi.TYPE_OBJECT,
                                                     properties={"firstname": openapi.Schema(type=openapi.TYPE_STRING),
                                                                 "lastname": openapi.Schema(type=openapi.TYPE_STRING),
                                                                 "email": openapi.Schema(type=openapi.TYPE_STRING)}))
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(responses={'200': openapi.Response("User found", UserCheckSerializer()),
                                    '404': openapi.Response("User not found"),
                                    '400': openapi.Response("Bad request")})
    @action(detail=True, methods=['get'], url_path="check")
    def check_user_existence(self, request, *args, **kwargs):
        exists, found = False, False
        try:
            user = self.get_object()
            exists = True
        except Http404:
            username = kwargs[self.lookup_field]
            try:
                user = users_service.check_user_existence(username=username)
                found = True
            except (ValueError, ServerError) as e:
                return Response(data={"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)
            except Http404:
                return Response(data={"message": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        res = {"username": user.username,
               "firstname": user.firstname,
               "lastname": user.lastname,
               "email": user.email,
               "already_exists": exists,
               "found": found}
        return Response(data=UserCheckSerializer(res).data, status=status.HTTP_200_OK)
