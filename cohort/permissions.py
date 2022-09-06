from rest_framework import permissions
from rest_framework.permissions import OR as drf_OR


class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.is_admin()

    def has_object_permission(self, request, view, obj):
        return request.user.is_admin()


class IsOwner(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        if obj == request.user:
            return True
        if hasattr(obj, "owner"):
            return obj.owner == request.user
        return False


def OR(*perms):
    if len(perms) < 1:
        raise ValueError("OR takes at list one Permission.")

    result = perms[0]
    for perm in perms[1:]:
        result = drf_OR(result, perm)
    return [result]
