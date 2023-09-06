from rest_framework import viewsets

from admin_cohort.tools.negative_limit_paginator import NegativeLimitOffsetPagination
from exports.permissions import ManageWorkspacesPermissions, ReadWorkspacesPermissions


class ExportsBaseViewSet(viewsets.ModelViewSet):
    lookup_field = "uuid"
    http_method_names = ["get", "post", "patch", "delete"]
    pagination_class = NegativeLimitOffsetPagination

    def get_permissions(self):
        if self.request.method in ['post', 'patch', 'delete']:
            return [ReadWorkspacesPermissions(), ManageWorkspacesPermissions()]
        return [ReadWorkspacesPermissions()]
