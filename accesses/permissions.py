from __future__ import annotations

from typing import List

from rest_framework import permissions
from rest_framework.permissions import IsAuthenticated, SAFE_METHODS

from accesses.models import Role
from accesses.services.accesses import accesses_service
from accesses.services.roles import roles_service
from admin_cohort.models import User


class IsAuthenticatedReadOnly(IsAuthenticated):
    def has_permission(self, request, view):
        authenticated = super().has_permission(request, view)
        return authenticated and request.method in SAFE_METHODS

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request=request, view=view)


def get_bound_roles(user: User) -> List[Role]:
    return [access.role for access in accesses_service.get_user_valid_accesses(user)]


def can_user_manage_accesses(user: User) -> bool:
    return any(filter(lambda role: roles_service.role_allows_to_manage_accesses(role), get_bound_roles(user)))


def can_user_read_accesses(user: User) -> bool:
    return any(filter(lambda role: roles_service.role_allows_to_read_accesses(role), get_bound_roles(user)))


def can_user_manage_users(user: User) -> bool:
    return any(filter(lambda role: role.right_manage_users, get_bound_roles(user)))


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


def can_user_make_export_csv_nomi(user: User):
    return any(filter(lambda role: role.right_export_csv_nominative, get_bound_roles(user)))


def can_user_make_export_csv_pseudo(user: User):
    return any(filter(lambda role: role.right_export_csv_pseudonymized, get_bound_roles(user)))


def can_user_read_datalabs(user: User) -> bool:
    return any(filter(lambda role: role.right_read_datalabs, get_bound_roles(user)))


def can_user_manage_datalabs(user: User) -> bool:
    return any(filter(lambda role: role.right_manage_datalabs, get_bound_roles(user)))


class RolesPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in ["POST", "PATCH", "DELETE"]:
            return accesses_service.user_is_full_admin(request.user)
        return request.method in permissions.SAFE_METHODS


class AccessesPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in ["POST", "PATCH", "DELETE"]:
            return can_user_manage_accesses(request.user)
        return request.method in permissions.SAFE_METHODS and can_user_read_accesses(request.user)

    def has_object_permission(self, request, view, obj):
        if request.method in ["PATCH", "DELETE"]:
            return accesses_service.can_user_manage_access(user=request.user, target_access=obj)
        return request.method == "GET" and accesses_service.can_user_read_access(user=request.user, target_access=obj)


class ProfilesPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in ("POST", "PATCH"):
            return can_user_manage_profiles(request.user)
        return request.method in permissions.SAFE_METHODS and can_user_read_profiles(request.user)

    def has_object_permission(self, request, view, obj):
        if request.method in ("GET", "PATCH"):
            return self.has_permission(request, view)
