import django_filters
from django_filters import OrderingFilter
from drf_yasg import openapi
from drf_yasg.openapi import Schema
from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from accesses.permissions import can_user_read_unix_accounts
from admin_cohort.models import User
from admin_cohort.permissions import OR, user_is_authenticated, IsAuthenticated
from admin_cohort.settings import RANGER_HIVE_POLICY_TYPES
from admin_cohort.views import YarnReadOnlyViewsetMixin
from workspaces.conf_workspaces import get_account_groups_from_id_aph
from workspaces.models import Account, Project, JupyterMachine, RangerHivePolicy, LdapGroup, Kernel
from workspaces.permissions import AccountPermissions
from workspaces.serializers import AccountSerializer, JupyterMachineSerializer, RangerHivePolicySerializer, \
                                   LdapGroupSerializer, KernelSerializer, ProjectSerializer, PublicProjectSerializer


class AccountFilter(django_filters.FilterSet):
    def search_filter(self, queryset, field, value):
        return queryset.filter(**{f'{field}__icontains': str(value)})

    def status_code_filter(self, queryset, field, value):
        return queryset.filter(**{f'{field}__in': [int(v) for v in str(value).upper().split(",")]})

    def include_distinct(self, queryset, field, value):
        return queryset.filter(**{f'{field}__in': [int(v) for v in str(value).upper().split(",")]}).distinct()

    kernels = django_filters.CharFilter(method="include_distinct")
    jupyter_machines = django_filters.CharFilter(method="include_distinct")
    ldap_groups = django_filters.CharFilter(method="include_distinct")
    ranger_hive_policy = django_filters.CharFilter(method="include_distinct")
    aphp_ldap_group_dn_search = django_filters.CharFilter(lookup_expr="icontains")

    ordering = OrderingFilter(fields=["username", "name", "firstname", "lastname", "mail"])

    class Meta:
        model = Account
        fields = [f.name for f in Account._meta.fields]


class AccountViewset(YarnReadOnlyViewsetMixin, viewsets.ModelViewSet):
    serializer_class = AccountSerializer
    queryset = Account.objects.all()
    lookup_field = "uid"
    filter_class = AccountFilter
    search_fields = ["username", "name", "firstname", "lastname", "mail"]
    swagger_tags = ['Workspaces - users']

    def get_serializer_context(self):
        return {'request': self.request}

    def get_permissions(self):
        return OR(AccountPermissions(),)

    def get_queryset(self):
        q = super(AccountViewset, self).get_queryset()
        user: User = self.request.user
        if not can_user_read_unix_accounts(user):
            ad_groups = get_account_groups_from_id_aph(user.provider_username)
            return q.filter(aphp_ldap_group_dn__in=ad_groups)
        return q

    @swagger_auto_schema(
        manual_parameters=list(map(
            lambda x: openapi.Parameter(
                name=x[0], in_=openapi.IN_QUERY, description=x[1], type=x[2],
                pattern=x[3] if len(x) == 4 else None
            ), [
                ["aphp_ldap_group_dn_search", "Search type",
                 openapi.TYPE_STRING],
                ["kernels", "Ids with ',' separator (1,2)",
                 openapi.TYPE_STRING],
                ["jupyter_machines", "Ids with ',' separator (1,2)",
                 openapi.TYPE_STRING],
                ["ldap_groups", "Ids with ',' separator (1,2)",
                 openapi.TYPE_STRING],
                ["ranger_hive_policy", "Ids with ',' separator (1,2)",
                 openapi.TYPE_STRING],
                [
                    "search",
                    f"Will search in multiple fields "
                    f"({', '.join(search_fields)})", openapi.TYPE_STRING
                ],
                [
                    "ordering",
                    f"To sort the result. Can be {', '.join(['username', 'name', 'firstname', 'lastname', 'mail'])}."
                    f"Use -field for descending order", openapi.TYPE_STRING
                ],
            ])))
    def list(self, request, *args, **kwargs):
        return super(AccountViewset, self).list(request, *args, **kwargs)


class ProjectViewset(YarnReadOnlyViewsetMixin, viewsets.ModelViewSet):
    serializer_class = ProjectSerializer
    queryset = Project.objects.all()
    lookup_field = "id"
    http_method_names = ["get"]

    swagger_tags = ['Workspaces - projects']

    def get_serializer_class(self):
        if user_is_authenticated(self.request.user) \
                and can_user_read_unix_accounts(self.request.user):
            return ProjectSerializer
        else:
            return PublicProjectSerializer


class JupyterMachineViewset(YarnReadOnlyViewsetMixin, viewsets.ModelViewSet):
    serializer_class = JupyterMachineSerializer
    queryset = JupyterMachine.objects.all()
    lookup_field = "id"
    http_method_names = ["get"]
    permission_classes = [AccountPermissions]

    swagger_tags = ['Workspaces - jupyter-machines']


class RangerHivePolicyViewset(YarnReadOnlyViewsetMixin, viewsets.ModelViewSet):
    serializer_class = RangerHivePolicySerializer
    queryset = RangerHivePolicy.objects.all()
    lookup_field = "id"
    http_method_names = ["get"]
    permission_classes = [AccountPermissions]

    swagger_tags = ['Workspaces - ranger-hive-policies']

    def get_permissions(self):
        if self.action in ['get_types']:
            return [IsAuthenticated()]
        return super(RangerHivePolicyViewset, self).get_permissions()

    @swagger_auto_schema(methods=['get'], manual_parameters=[], responses={
        status.HTTP_200_OK: openapi.Response(
            description="Available types for Ranger Hive Policy",
            schema=Schema(
                title='List of types', type=openapi.TYPE_ARRAY,
                items=Schema(type=openapi.TYPE_STRING)))
    })
    @action(detail=False, methods=['get'], url_path="types")
    def get_types(self, request: Request):
        return Response(RANGER_HIVE_POLICY_TYPES, status=status.HTTP_200_OK)


class LdapGroupViewset(YarnReadOnlyViewsetMixin, viewsets.ModelViewSet):
    serializer_class = LdapGroupSerializer
    queryset = LdapGroup.objects.all()
    lookup_field = "id"
    http_method_names = ["get"]
    permission_classes = [AccountPermissions]

    swagger_tags = ['Workspaces - ldap-groups']


class KernelViewset(YarnReadOnlyViewsetMixin, viewsets.ModelViewSet):
    serializer_class = KernelSerializer
    queryset = Kernel.objects.all()
    lookup_field = "id"
    http_method_names = ["get"]
    permission_classes = [AccountPermissions]

    swagger_tags = ['Workspaces - kernels']
