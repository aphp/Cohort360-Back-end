from __future__ import annotations

from typing import List

from rest_framework import permissions

from accesses.models import Role, Perimeter
from accesses.services.access import accesses_service
from admin_cohort.models import User


def get_bound_roles(user: User) -> List[Role]:
    return [access.role for access in accesses_service.get_user_valid_accesses(user)]


def user_is_full_admin(user: User) -> bool:
    return any(filter(lambda role: role.right_full_admin, get_bound_roles(user)))


def can_user_manage_roles(user: User) -> bool:
    return any(filter(lambda role: role.right_manage_roles, get_bound_roles(user)))


def can_user_read_roles(user: User) -> bool:
    return any(filter(lambda role: role.right_read_roles, get_bound_roles(user)))


def can_user_manage_access(user: User, role: Role, perimeter: Perimeter) -> bool:
    return accesses_service.can_user_manage_access(user, role, perimeter)


def can_user_read_access(user: User, role: Role, perimeter: Perimeter) -> bool:
    return accesses_service.can_user_read_access(user, role, perimeter)


def can_user_manage_accesses(user: User) -> bool:
    return any(filter(lambda role: role.can_manage_accesses, get_bound_roles(user)))


def can_user_read_accesses(user: User) -> bool:
    return any(filter(lambda role: role.can_read_accesses, get_bound_roles(user)))


def can_user_read_users(user: User) -> bool:
    return any(filter(lambda role: role.right_read_users, get_bound_roles(user)))


def can_user_read_logs(user: User) -> bool:
    return any(filter(lambda role: role.right_read_logs, get_bound_roles(user)))


def can_user_manage_profiles(user: User) -> bool:
    return any(filter(lambda role: role.right_manage_users, get_bound_roles(user)))


def can_user_read_profiles(user: User) -> bool:
    return any(filter(lambda role: role.right_read_users, get_bound_roles(user)))


def can_user_make_export_jupyter_nomi(user: User):
    return any(filter(lambda role: role.right_export_jupyter_nominative, get_bound_roles(user)))


def can_user_make_export_jupyter_pseudo(user: User):
    return any(filter(lambda role: role.right_export_jupyter_pseudonymized, get_bound_roles(user)))


def can_user_make_csv_export(user: User) -> bool:
    return any(filter(lambda role: role.right_export_csv_nominative or role.right_export_csv_pseudonymized,
                      get_bound_roles(user)))


def can_user_make_jupyter_export(user: User) -> bool:
    return any(filter(lambda role: role.right_export_jupyter_nominative or role.right_export_jupyter_pseudonymized,
                      get_bound_roles(user)))


def can_user_read_datalabs(user: User) -> bool:
    return any(filter(lambda role: role.right_read_datalabs, get_bound_roles(user)))


def can_user_manage_datalabs(user: User) -> bool:
    return any(filter(lambda role: role.right_manage_datalabs, get_bound_roles(user)))


class RolesPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in ["POST", "PATCH", "DELETE"]:
            return can_user_manage_roles(request.user)
        return request.method in permissions.SAFE_METHODS and can_user_read_roles(request.user)


class AccessesPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in ["POST", "PATCH", "DELETE"]:
            if can_user_manage_accesses(request.user):
                if request.method == "POST":
                    role = Role.objects.get(pk=request.data.get("role_id"))
                    perimeter = Perimeter.objects.get(pk=request.data.get("perimeter_id"))
                    return can_user_manage_access(request.user, role, perimeter)    # check whether can user assign role when creating new access
                return True
        return request.method in permissions.SAFE_METHODS and can_user_read_accesses(request.user)

    def has_object_permission(self, request, view, obj):
        if request.method in ["PATCH", "DELETE"]:
            return can_user_manage_access(request.user, obj.role, obj.perimeter)
        return request.method == "GET" and can_user_read_access(request.user, obj.role, obj.perimeter)


class ProfilesPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in ("POST", "PATCH"):
            return can_user_manage_profiles(request.user)
        return request.method in permissions.SAFE_METHODS and can_user_read_profiles(request.user)

    def has_object_permission(self, request, view, obj):
        if request.method in ("GET", "PATCH"):
            return self.has_permission(request, view)
