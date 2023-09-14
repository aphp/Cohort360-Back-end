from django.db.models.query import QuerySet
from rest_framework import permissions
from rest_framework.permissions import OR as drf_OR

from admin_cohort.models import User
from admin_cohort.settings import ETL_USERNAME, ADMINS


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
    from accesses.models import get_user_valid_manual_accesses, Role

    accesses = get_user_valid_manual_accesses(user)
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
        user = request.user
        return user_is_authenticated(user) and (can_user_edit_roles(user) or user.provider_username == ETL_USERNAME)


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


def can_user_add_users(user: User) -> bool:
    return any([r.right_add_users for r in get_bound_roles(user)])


def can_user_edit_users(user: User) -> bool:
    return any([r.right_edit_users for r in get_bound_roles(user)])


class UsersPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        if not user_is_authenticated(request.user):
            return False
        if request.method == "POST":
            return can_user_add_users(request.user)
        if request.method == "PATCH":
            return can_user_edit_users(request.user)
        return request.method in permissions.SAFE_METHODS and can_user_read_users(request.user)

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request=request, view=view)


class CachePermission(permissions.BasePermission):
    def has_permission(self, request, view):
        is_allowed_method = request.method.lower() in ["get", "delete"]
        user = request.user
        admins_emails = [a[1] for a in ADMINS]
        return (user_is_authenticated(user)
                and is_allowed_method
                and user.email in admins_emails)


def either(*perms):
    if not perms:
        raise ValueError("OR takes at list one Permission.")

    result = perms[0]
    for perm in perms[1:]:
        result = drf_OR(result, perm)
    return [result]
