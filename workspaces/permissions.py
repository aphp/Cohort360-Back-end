from rest_framework import permissions

from accesses.permissions import can_user_read_datalabs
from admin_cohort.permissions import user_is_authenticated


class AccountsPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        # todo: check if user had a unix account (needs to call Infra API)
        if not user_is_authenticated(request.user):
            return False
        return request.method in permissions.SAFE_METHODS and \
            can_user_read_datalabs(request.user.provider_username)

    def has_object_permission(self, request, view, obj):
        # todo: check if user is owner of unix_account (needs to call Infra API)
        if not user_is_authenticated(request.user):
            return False
        if request.method in permissions.SAFE_METHODS:
            return can_user_read_datalabs(request.user)
        else:
            return False
