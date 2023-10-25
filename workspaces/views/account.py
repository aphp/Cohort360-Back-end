from django_filters import rest_framework as filters, OrderingFilter
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets

from exports.permissions import can_user_read_datalabs
from admin_cohort.models import User
from workspaces.conf_workspaces import get_account_groups_from_id_aph
from workspaces.models import Account
from workspaces.permissions import AccountsPermission
from workspaces.serializers import AccountSerializer


class AccountFilter(filters.FilterSet):
    def search_filter(self, queryset, field, value):
        return queryset.filter(**{f'{field}__icontains': str(value)})

    def status_code_filter(self, queryset, field, value):
        return queryset.filter(**{f'{field}__in': [int(v) for v in str(value).upper().split(",")]})

    def include_distinct(self, queryset, field, value):
        return queryset.filter(**{f'{field}__in': [int(v) for v in str(value).upper().split(",")]}).distinct()

    kernels = filters.CharFilter(method="include_distinct")
    jupyter_machines = filters.CharFilter(method="include_distinct")
    ldap_groups = filters.CharFilter(method="include_distinct")
    ranger_hive_policy = filters.CharFilter(method="include_distinct")
    aphp_ldap_group_dn_search = filters.CharFilter(lookup_expr="icontains")

    ordering = OrderingFilter(fields=("username", "name", "firstname", "lastname", "mail"))

    class Meta:
        model = Account
        fields = [f.name for f in Account._meta.fields]


class AccountViewSet(viewsets.ModelViewSet):
    serializer_class = AccountSerializer
    queryset = Account.objects.all()
    lookup_field = "uid"
    http_method_names = ["get"]
    permission_classes = [AccountsPermission]
    filterset_class = AccountFilter
    search_fields = ["username", "name", "firstname", "lastname", "mail"]
    swagger_tags = ['Workspaces - users']

    def get_serializer_context(self):
        return {'request': self.request}

    def get_queryset(self):
        q = super(AccountViewSet, self).get_queryset()
        user: User = self.request.user
        if not user.is_anonymous and not can_user_read_datalabs(user):
            ad_groups = get_account_groups_from_id_aph(user.provider_username)
            return q.filter(aphp_ldap_group_dn__in=ad_groups)
        return q

    @swagger_auto_schema(manual_parameters=list(map(lambda x: openapi.Parameter(name=x[0], in_=openapi.IN_QUERY,
                                                                                description=x[1], type=x[2],
                                                                                pattern=x[3] if len(x) == 4 else None),
                                                    [["aphp_ldap_group_dn_search", "Search type", openapi.TYPE_STRING],
                                                     ["kernels", "Ids with ',' separator (1,2)", openapi.TYPE_STRING],
                                                     ["jupyter_machines", "Ids with ',' separator (1,2)",
                                                      openapi.TYPE_STRING],
                                                     ["ldap_groups", "Ids with ',' separator (1,2)",
                                                      openapi.TYPE_STRING],
                                                     ["ranger_hive_policy", "Ids with ',' separator (1,2)",
                                                      openapi.TYPE_STRING],
                                                     ["search", f"Will search in multiple fields "
                                                                f"({', '.join(search_fields)})", openapi.TYPE_STRING],
                                                     ["ordering", f"To sort the result. Can be "
                                                                  f"{', '.join(search_fields)}. Use -field for "
                                                                  f"descending order", openapi.TYPE_STRING]])))
    def list(self, request, *args, **kwargs):
        return super(AccountViewSet, self).list(request, *args, **kwargs)
