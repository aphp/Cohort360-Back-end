from django.db.models.query import QuerySet
from rest_framework import permissions
from rest_framework.permissions import OR as drf_OR

from accesses.models import Role
from accesses.tools import get_user_valid_manual_accesses
from admin_cohort.models import User
from admin_cohort.settings import ETL_USERNAME


def user_is_authenticated(user):
    return user and hasattr(user, User.USERNAME_FIELD)


def get_bound_roles(user: User) -> QuerySet:
    """
    Check all valid accesses from a provider and retrieves all the roles
    indirectly bound to them
    @param user:
    @type user: User
    @return:
    @rtype:
    """

    accesses = get_user_valid_manual_accesses(user)
    return Role.objects.filter(id__in=[a.role_id for a in accesses])


def user_is_full_admin(user: User) -> bool:
    return any(filter(lambda role: role.right_full_admin, get_bound_roles(user)))


def can_user_read_users(user: User) -> bool:
    return any(filter(lambda role: role.right_read_users, get_bound_roles(user)))


def can_user_read_logs(user: User) -> bool:
    return any(filter(lambda role: role.right_read_logs, get_bound_roles(user)))


class MaintenancesPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        user = request.user
        return user_is_authenticated(user) and (user_is_full_admin(user) or
                                                user.provider_username == ETL_USERNAME)


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
        return request.method in permissions.SAFE_METHODS and can_user_read_users(request.user)

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request=request, view=view)


class CachePermission(permissions.BasePermission):
    def has_permission(self, request, view):
        return user_is_authenticated(user=request.user) \
            and request.method in ["GET", "DELETE"] \
            and user_is_full_admin(user=request.user)


def either(*perms):
    if not perms:
        raise ValueError("OR takes at list one Permission.")

    result = perms[0]
    for perm in perms[1:]:
        result = drf_OR(result, perm)
    return [result]
