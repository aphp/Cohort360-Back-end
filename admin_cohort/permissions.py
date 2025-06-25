import os

from rest_framework.permissions import OR as DRF_OR, IsAuthenticated, SAFE_METHODS

from accesses.permissions import can_user_manage_users
from accesses.services.accesses import accesses_service

ROLLOUT_USERNAME = os.environ.get("ROLLOUT_USERNAME", "ROLLOUT_PIPELINE")


def user_is_authenticated(user):
    return not user.is_anonymous


class MaintenancesPermission(IsAuthenticated):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        authenticated = super().has_permission(request, view)
        user = request.user
        return authenticated and (accesses_service.user_is_full_admin(user) or
                                  user.username == ROLLOUT_USERNAME)


class LogsPermission(IsAuthenticated):
    def has_permission(self, request, view):
        authenticated = super().has_permission(request, view)
        return authenticated and accesses_service.user_is_full_admin(request.user)

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request=request, view=view)


class UsersPermission(IsAuthenticated):
    def has_permission(self, request, view):
        authenticated = super().has_permission(request, view)
        return authenticated and \
            (request.method == "GET" or
             (request.method in ("POST", "PATCH") and can_user_manage_users(request.user)))

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)


class CachePermission(IsAuthenticated):
    def has_permission(self, request, view):
        authenticated = super().has_permission(request, view)
        return authenticated and \
            request.method in ["GET", "DELETE"] and \
            accesses_service.user_is_full_admin(user=request.user)


def either(*perms):
    if not perms:
        raise ValueError("OR takes at list one Permission.")

    result = perms[0]
    for perm in perms[1:]:
        result = DRF_OR(result, perm)
    return [result]
