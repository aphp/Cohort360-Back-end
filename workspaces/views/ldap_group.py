from rest_framework import viewsets

from workspaces.models.ldap_group import LdapGroup
from workspaces.permissions import AccountPermissions
from workspaces.serializers import LdapGroupSerializer


class LdapGroupViewSet(viewsets.ModelViewSet):
    serializer_class = LdapGroupSerializer
    queryset = LdapGroup.objects.all()
    lookup_field = "id"
    http_method_names = ["get"]
    permission_classes = [AccountPermissions]

    swagger_tags = ['Workspaces - ldap-groups']
