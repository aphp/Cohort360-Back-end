from rest_framework import permissions

from accesses.models import Role, do_user_accesses_allow_to_manage_role, Perimeter
from admin_cohort.models import User
from admin_cohort.permissions import get_bound_roles


def can_user_manage_roles(user: User) -> bool:
    return any(filter(lambda role: role.right_manage_roles, get_bound_roles(user)))


def can_user_read_roles(user: User) -> bool:
    return any(filter(lambda role: role.right_read_roles, get_bound_roles(user)))


def can_user_manage_access(user: User, role: Role, perimeter: Perimeter) -> bool:
    return do_user_accesses_allow_to_manage_role(user, role, perimeter)


def can_user_read_access(user: User, role: Role, perimeter: Perimeter) -> bool:
    return do_user_accesses_allow_to_manage_role(user, role, perimeter, readonly=True)


def can_user_manage_accesses(user: User) -> bool:
    return any(filter(lambda role: role.can_manage_accesses, get_bound_roles(user)))


def can_user_read_accesses(user: User) -> bool:
    return any(filter(lambda role: role.can_read_accesses, get_bound_roles(user)))


def can_user_manage_profiles(user: User) -> bool:
    return any(filter(lambda role: role.right_manage_users, get_bound_roles(user)))


def can_user_read_profiles(user: User) -> bool:
    return any(filter(lambda role: role.right_read_users, get_bound_roles(user)))


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
                    role_id = request.data.get("role_id")
                    perimeter_id = request.data.get("care_site_id")
                    role = Role.objects.get(pk=role_id)
                    perimeter = Perimeter.objects.get(pk=perimeter_id)
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
