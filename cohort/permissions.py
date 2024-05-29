from rest_framework import permissions


class IsOwnerPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if hasattr(obj, "owner"):
            return obj.owner == request.user
        return False
