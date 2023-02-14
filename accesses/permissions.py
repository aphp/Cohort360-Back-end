from rest_framework import permissions

from accesses.models import Role, \
    get_all_user_managing_accesses_on_perimeter, can_roles_manage_access, \
    Perimeter
from admin_cohort.models import User
from admin_cohort.permissions import get_bound_roles, \
    can_user_edit_roles, can_user_read_users


def can_user_manage_access(
        user: User, role: Role, perimeter: Perimeter
) -> bool:
    user_accesses = get_all_user_managing_accesses_on_perimeter(user, perimeter)
    return can_roles_manage_access(list(user_accesses), role, perimeter)


def can_user_manage_accesses(user: User) -> bool:
    """
    Will check the accesses of the Provider,
    Retrieve the roles bound to those,
    And return True if one of these roles allow to manage one kind of accesses
    @param user:
    @type user: User
    @return: if user can manage at least one type of accesses
    @rtype: bool
    """
    # Actual permission will depend on the data posted (perimeter_id, role_id)
    return any([r.can_manage_other_accesses for r in get_bound_roles(user)])


def can_user_manage_review_transfer_jupyter_accesses(user: User) -> bool:
    """
    Will check the accesses of the Provider,
    Retrieve the roles bound to those,
    And return True if one of these roles
    allow to manage review_transfer_jupyter accesses
    @param user:
    @type user: User
    @return: if user can manage at least one type of accesses
    @rtype: bool
    """
    return any([r.right_manage_review_transfer_jupyter
                for r in get_bound_roles(user)])


def can_user_manage_transfer_jupyter_accesses(user: User) -> bool:
    """
    Will check the accesses of the Provider,
    Retrieve the roles bound to those,
    And return True if one of these roles
    allow to manage transfer_jupyter accesses
    @param user:
    @type user: User
    @return: if user can manage at least one type of accesses
    @rtype: bool
    """
    return any([r.right_manage_transfer_jupyter
                for r in get_bound_roles(user)])


def can_user_manage_review_export_csv_accesses(user: User) -> bool:
    """
    Will check the accesses of the Provider,
    Retrieve the roles bound to those,
    And return True if one of these roles
    allow to manage review_export_csv accesses
    @param user:
    @type user: User
    @return: if user can manage at least one type of accesses
    @rtype: bool
    """
    return any([r.right_manage_review_export_csv
                for r in get_bound_roles(user)])


def can_user_manage_export_csv_accesses(user: User) -> bool:
    """
    Will check the accesses of the Provider,
    Retrieve the roles bound to those,
    And return True if one of these roles allow to manage export_csv accesses
    @param user:
    @type user: User
    @return: if user can manage at least one type of accesses
    @rtype: bool
    """
    return any([r.right_manage_export_csv for r in get_bound_roles(user)])


def can_user_read_accesses(user: User) -> bool:
    return any([r.can_read_other_accesses for r in get_bound_roles(user)])


def can_user_read_access(user: User, role: Role, perimeter: Perimeter) -> bool:
    user_accesses = get_all_user_managing_accesses_on_perimeter(user, perimeter)
    return can_roles_manage_access(
        list(user_accesses), role, perimeter, just_read=True
    )


def can_user_edit_profiles(user: User) -> bool:
    return any([r.right_edit_users for r in get_bound_roles(user)])


def can_user_add_profiles(user: User) -> bool:
    return any([r.right_add_users for r in get_bound_roles(user)])


class RolePermissions(permissions.BasePermission):
    def has_permission(self, request, view):
        # in list, objects will be serialized given the user's rights
        if request.method in ["PUT", "PATCH", "POST", "DELETE"]:
            return can_user_edit_roles(request.user.provider_username)
        return request.method in permissions.SAFE_METHODS

    def has_object_permission(self, request, view, obj):
        if request.method in ["PUT", "PATCH", "POST"]:
            return can_user_edit_roles(request.user.provider_username)
        elif request.method == "GET":
            return True
        else:
            return False


class AccessPermissions(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in ["POST", "PUT", "PATCH", "DELETE"]:
            return can_user_manage_accesses(request.user)

        # in list, objects will be filtered given the user's rights
        # todo : totest
        return (request.method in permissions.SAFE_METHODS
                and can_user_read_accesses(request.user))

    def has_object_permission(self, request, view, obj):
        if request.method in ["PUT", "PATCH", "DELETE"]:
            return can_user_manage_access(request.user, obj.role, obj.perimeter)
        elif request.method == "GET":
            return can_user_read_access(request.user, obj.role, obj.perimeter)
        else:
            return False


class HasUserAddingPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        return can_user_edit_profiles(request.user)


class ProfilePermissions(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in ["POST"]:
            return can_user_add_profiles(request.user)
        if request.method in ["PATCH"]:
            return can_user_edit_profiles(request.user)
        # in list, objects will be serialized given the user's rights
        # todo : totest
        return (request.method in permissions.SAFE_METHODS
                and can_user_read_users(request.user))

    def has_object_permission(self, request, view, obj):
        if request.method in ["POST", "PATCH"]:
            return can_user_edit_profiles(request.user)
        elif request.method == "GET":
            return True
        else:
            return False


# WORKSPACES


def can_user_read_unix_accounts(user: User) -> bool:
    return any([
        r.right_read_env_unix_users for r in get_bound_roles(user)
    ])


def can_user_manage_unix_accounts(user: User) -> bool:
    return any([
        r.right_manage_env_unix_users for r in get_bound_roles(user)
    ])
