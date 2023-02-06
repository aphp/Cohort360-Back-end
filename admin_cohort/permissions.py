from django.db.models.query import QuerySet
from rest_framework import permissions
from rest_framework.permissions import OR as drf_OR

from admin_cohort.models import User


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
    from accesses.models import get_user_valid_manual_accesses_queryset, Role

    accesses = get_user_valid_manual_accesses_queryset(user)
    return Role.objects.filter(id__in=[a.role_id for a in accesses])


def can_user_read_users(user: User) -> bool:
    return any([r.right_read_users for r in get_bound_roles(user)])


def can_user_edit_roles(user: User) -> bool:
    return any([r.right_edit_roles for r in get_bound_roles(user)])


def can_user_read_logs(user: User) -> bool:
    return any([
        r.right_read_logs or r.right_edit_roles
        for r in get_bound_roles(user)
    ])


class MaintenancePermission(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return can_user_edit_roles(request.user.provider_username)


class LogsPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method != "GET":
            return False
        if not user_is_authenticated(request.user):
            return False
        return can_user_read_logs(request.user)

    def has_object_permission(self, request, view, obj):
        if request.method != "GET":
            return False
        if not user_is_authenticated(request.user):
            return False
        return can_user_read_logs(request.user)


class IsAuthenticated(permissions.BasePermission):
    def has_permission(self, request, view):
        return user_is_authenticated(request.user)

    def has_object_permission(self, request, view, obj):
        return user_is_authenticated(request.user)


class IsAuthenticatedReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if not user_is_authenticated(request.user):
            return False
        return request.method in permissions.SAFE_METHODS

    def has_object_permission(self, request, view, obj):
        if not user_is_authenticated(request.user):
            return False
        return request.method in permissions.SAFE_METHODS


class IsAuthenticatedReadOnlyListOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if not user_is_authenticated(request.user):
            return False
        return request.method in permissions.SAFE_METHODS

    def has_object_permission(self, request, view, obj):
        return False


def OR(*perms):
    if len(perms) < 1:
        raise ValueError("OR takes at list one Permission.")

    result = perms[0]
    for perm in perms[1:]:
        result = drf_OR(result, perm)
    return [result]
