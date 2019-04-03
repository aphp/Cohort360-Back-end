from rest_framework import permissions


class IsOwner(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        return obj.user == request.user


class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user:
            return False
        if not request.user.is_authenticated:
            return False
        return request.user.is_admin()