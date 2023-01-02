from django_filters import rest_framework as filters

from admin_cohort.permissions import OR
from exports.permissions import AnnexesPermissions, can_review_transfer_jupyter, can_review_export_csv
from exports.serializers import AnnexeAccountSerializer
from workspaces.conf_workspaces import get_account_groups_from_id_aph
from workspaces.models import Account
from workspaces.permissions import AccountPermissions
from workspaces.views import AccountViewSet


class UnixAccountFilter(filters.FilterSet):
    def provider_source_value_filter(self, queryset, field, value):
        return queryset.filter(aphp_ldap_group_dn__in=get_account_groups_from_id_aph(value))

    provider_source_value = filters.CharFilter(field_name='provider_source_value',
                                               method="provider_source_value_filter")

    class Meta:
        model = Account
        fields = ("provider_source_value",)


class UnixAccountViewSet(AccountViewSet):
    lookup_field = "uid"
    serializer_class = AnnexeAccountSerializer
    http_method_names = ["get"]
    swagger_tags = ['Exports - users']
    filterset_class = UnixAccountFilter

    def get_permissions(self):
        return OR(AnnexesPermissions(), AccountPermissions())

    def get_queryset(self):
        q = super(UnixAccountViewSet, self).get_queryset()
        user = self.request.user
        if not can_review_transfer_jupyter(user) and not can_review_export_csv(user):
            ad_groups = get_account_groups_from_id_aph(user)
            return q.filter(aphp_ldap_group_dn__in=ad_groups)
        return q

    def list(self, request, *args, **kwargs):
        return super(UnixAccountViewSet, self).list(request, *args, **kwargs)
