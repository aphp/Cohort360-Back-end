from django.conf import settings
from rest_framework import permissions


class SJSorETLCallbackPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and \
            request.method in ("GET", "PATCH") and \
            request.user.username in settings.APPLICATIVE_USERS.values()

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)
