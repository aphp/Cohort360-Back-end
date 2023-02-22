from rest_framework import permissions

from accesses.models import Role, get_all_user_managing_accesses_on_perimeter, can_roles_manage_access, Perimeter
from admin_cohort.models import User
from admin_cohort.permissions import get_bound_roles, can_user_edit_roles, can_user_read_users


def can_user_manage_access(user: User, role: Role, perimeter: Perimeter) -> bool:
    user_accesses = get_all_user_managing_accesses_on_perimeter(user, perimeter)
    return can_roles_manage_access(list(user_accesses), role, perimeter)


def can_user_manage_accesses(user: User) -> bool:
    return any([r.can_manage_other_accesses for r in get_bound_roles(user)])


def can_user_manage_review_transfer_jupyter_accesses(user: User) -> bool:
    return any([r.right_manage_review_transfer_jupyter for r in get_bound_roles(user)])


def can_user_manage_transfer_jupyter_accesses(user: User) -> bool:
    return any([r.right_manage_transfer_jupyter for r in get_bound_roles(user)])


def can_user_manage_review_export_csv_accesses(user: User) -> bool:
    return any([r.right_manage_review_export_csv for r in get_bound_roles(user)])


def can_user_manage_export_csv_accesses(user: User) -> bool:
    return any([r.right_manage_export_csv for r in get_bound_roles(user)])


def can_user_read_accesses(user: User) -> bool:
    return any([r.can_read_other_accesses for r in get_bound_roles(user)])


def can_user_read_access(user: User, role: Role, perimeter: Perimeter) -> bool:
    user_accesses = get_all_user_managing_accesses_on_perimeter(user, perimeter)
    return can_roles_manage_access(list(user_accesses), role, perimeter, just_read=True)


def can_user_edit_profiles(user: User) -> bool:
    return any([r.right_edit_users for r in get_bound_roles(user)])


def can_user_add_profiles(user: User) -> bool:
    return any([r.right_add_users for r in get_bound_roles(user)])


class RolePermissions(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in ["PUT", "PATCH", "POST", "DELETE"]:
            return can_user_edit_roles(request.user.provider_username)
        return request.method in permissions.SAFE_METHODS

    def has_object_permission(self, request, view, obj):
        if request.method in ["PUT", "PATCH", "POST"]:
            return can_user_edit_roles(request.user.provider_username)
        return request.method == "GET"


class AccessPermissions(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in ["POST", "PUT", "PATCH", "DELETE"]:
            return can_user_manage_accesses(request.user)

        return request.method in permissions.SAFE_METHODS and can_user_read_accesses(request.user)

    def has_object_permission(self, request, view, obj):
        if request.method in ["PUT", "PATCH", "DELETE"]:
            y = can_user_manage_access(request.user, obj.role, obj.perimeter)
            return y
        return request.method == "GET" and can_user_read_access(request.user, obj.role, obj.perimeter)


class HasUserAddingPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        return can_user_edit_profiles(request.user)


class ProfilePermissions(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method == "POST":
            return can_user_add_profiles(request.user)
        if request.method == "PATCH":
            return can_user_edit_profiles(request.user)
        return request.method in permissions.SAFE_METHODS and can_user_read_users(request.user)

    def has_object_permission(self, request, view, obj):
        if request.method in ["POST", "PATCH"]:
            return can_user_edit_profiles(request.user)
        return request.method == "GET"


# WORKSPACES


def can_user_read_unix_accounts(user: User) -> bool:
    return any([r.right_read_env_unix_users for r in get_bound_roles(user)])


def can_user_manage_unix_accounts(user: User) -> bool:
    return any([r.right_manage_env_unix_users for r in get_bound_roles(user)])
