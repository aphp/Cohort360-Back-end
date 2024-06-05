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
from admin_cohort.types import ServerError, MissingDataError
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
    search_fields = ["firstname", "lastname", "username", "email"]
    filterset_class = UserFilter
    permission_classes = (UsersPermission,)
    http_method_names = ["get", "patch"]

    def get_serializer_context(self):
        return {'request': self.request}

    def get_queryset(self):
        # todo : to test manual_only
        manual_only = self.request.GET.get("manual_only")
        if not manual_only:
            return super(UserViewSet, self).get_queryset()
        return User.objects.filter(profiles__source='Manual').distinct()

    @swagger_auto_schema(manual_parameters=list(map(lambda x: openapi.Parameter(name=x[0], in_=openapi.IN_QUERY,
                                                                                description=x[1], type=x[2],
                                                                                pattern=x[3] if len(x) == 4 else None),
                                                    [["manual_only", "If True, only return users with a `manual` profile", openapi.TYPE_BOOLEAN],
                                                     ["firstname", "Search type", openapi.TYPE_STRING],
                                                     ["lastname", "Filter type", openapi.TYPE_STRING],
                                                     ["username", "Search type", openapi.TYPE_STRING],
                                                     ["email", "Search type", openapi.TYPE_STRING],
                                                     ["ordering", "Which field to use when ordering the results (firstname, lastname, "
                                                                  "username, email)",
                                                      openapi.TYPE_STRING],
                                                     ["search", "A search term on multiple fields (firstname, lastname, username email)",
                                                      openapi.TYPE_STRING],
                                                     ["page", "A page number within the paginated result set.", openapi.TYPE_INTEGER]])))
    @cache_response()
    def list(self, request, *args, **kwargs):
        return super(UserViewSet, self).list(request, *args, **kwargs)

    @swagger_auto_schema(request_body=openapi.Schema(type=openapi.TYPE_OBJECT,
                                                     properties={"firstname": openapi.Schema(type=openapi.TYPE_STRING),
                                                                 "lastname": openapi.Schema(type=openapi.TYPE_STRING),
                                                                 "email": openapi.Schema(type=openapi.TYPE_STRING)}))
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(responses={'200': openapi.Response("Profile found", UserCheckSerializer()),
                                    '204': openapi.Response("No user found matching the given username"),
                                    '400': openapi.Response("Bad request"),
                                    '500': openapi.Response("Server error")})
    @action(detail=False, methods=['get'], url_path="check")
    def check_existing_user(self, request, *args, **kwargs):
        try:
            res = self.get_object()
        except Http404:
            res = users_service.check_existing_user(username=request.data.get("username"))
            return Response(data=UserCheckSerializer(res).data, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response(data={"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except ServerError as e:
            return Response(data={"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except MissingDataError as e:
            return Response(data={"error": f"User not found - {e}"}, status=status.HTTP_204_NO_CONTENT)
