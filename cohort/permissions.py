from rest_framework import permissions

from admin_cohort.permissions import user_is_authenticated
from admin_cohort.settings import ETL_USERNAME, SJS_USERNAME


class IsOwnerPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if hasattr(obj, "owner"):
            return obj.owner == request.user
        return False


class SJSorETLCallbackPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        return user_is_authenticated(request.user)

    def has_object_permission(self, request, view, obj):
        return user_is_authenticated(request.user) and \
            request.method in ("GET", "PATCH") and \
            request.user.provider_username in [SJS_USERNAME, ETL_USERNAME]
