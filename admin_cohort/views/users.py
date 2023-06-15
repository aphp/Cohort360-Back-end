from django_filters import rest_framework as filters, OrderingFilter
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from admin_cohort.models import User
from admin_cohort.permissions import IsAuthenticatedReadOnly, can_user_read_users
from admin_cohort.serializers import UserSerializer, OpenUserSerializer
from admin_cohort.views import YarnReadOnlyViewsetMixin, BaseViewset


class UserFilter(filters.FilterSet):
    ordering = OrderingFilter(fields=('firstname', "lastname", "provider_username", "email"))

    class Meta:
        model = User
        fields = ['firstname', "lastname", "provider_username", "email"]


class UserViewSet(YarnReadOnlyViewsetMixin, BaseViewset):
    queryset = User.objects.all()
    lookup_field = "provider_username"
    search_fields = ["firstname", "lastname", "provider_username", "email"]
    filterset_class = UserFilter
    permission_classes = (IsAuthenticatedReadOnly,)

    def get_serializer_context(self):
        return {'request': self.request}

    def get_serializer(self, *args, **kwargs):
        if can_user_read_users(self.request.user):
            return UserSerializer(*args, **kwargs)
        return OpenUserSerializer(*args, **kwargs)

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
                                                     ["provider_username", "Search type", openapi.TYPE_STRING],
                                                     ["email", "Search type", openapi.TYPE_STRING],
                                                     ["ordering", "Which field to use when ordering the results (firstname, lastname, "
                                                                  "provider_username, email)",
                                                      openapi.TYPE_STRING],
                                                     ["search", "A search term on multiple fields (firstname, lastname, provider_username email)",
                                                      openapi.TYPE_STRING],
                                                     ["page", "A page number within the paginated result set.", openapi.TYPE_INTEGER]])))
    def list(self, request, *args, **kwargs):
        return super(UserViewSet, self).list(request, *args, **kwargs)