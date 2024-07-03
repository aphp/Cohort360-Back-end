from django.conf import settings
from rest_framework import permissions
from rest_framework.permissions import OR as drf_OR

from accesses.permissions import can_user_read_users, can_user_read_logs, can_user_manage_users
from accesses.services.accesses import accesses_service
from admin_cohort.models import User


def user_is_authenticated(user):
    return user and hasattr(user, User.USERNAME_FIELD)


class MaintenancesPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        user = request.user
        return user_is_authenticated(user) and (accesses_service.user_is_full_admin(user) or
                                                user.username == settings.ROLLOUT_USERNAME or
                                                user.username in getattr(settings, "applicative_users", []))


class LogsPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method != "GET" or not user_is_authenticated(request.user):
            return False
        return can_user_read_logs(request.user)

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request=request, view=view)


class IsAuthenticated(permissions.BasePermission):
    def has_permission(self, request, view):
        return user_is_authenticated(request.user)

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request=request, view=view)


class IsAuthenticatedReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if not user_is_authenticated(request.user):
            return False
        return request.method in permissions.SAFE_METHODS

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request=request, view=view)


class UsersPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        if not user_is_authenticated(request.user):
            return False
        return request.method == "GET" and (view.detail or can_user_read_users(request.user)) \
            or (request.method == "PATCH" and can_user_manage_users(request.user))

    def has_object_permission(self, request, view, obj):
        return request.user.pk == obj.pk or can_user_read_users(request.user)


class CachePermission(permissions.BasePermission):
    def has_permission(self, request, view):
        return user_is_authenticated(user=request.user) \
            and request.method in ["GET", "DELETE"] \
            and accesses_service.user_is_full_admin(user=request.user)


def either(*perms):
    if not perms:
        raise ValueError("OR takes at list one Permission.")

    result = perms[0]
    for perm in perms[1:]:
        result = drf_OR(result, perm)
    return [result]
