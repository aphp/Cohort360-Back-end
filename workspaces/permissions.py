from rest_framework import permissions

from accesses.permissions import can_user_read_unix_accounts
from admin_cohort.permissions import user_is_authenticated


def has_user_one_unix_account(provider_source_value: str) -> bool:
    # will require request to API infra
    return False


def is_user_owner_of_unix_account():
    # will require request to API infra
    return False


class AccountPermissions(permissions.BasePermission):
    def has_permission(self, request, view):
        if not user_is_authenticated(request.user):
            return False
        return \
            request.method in permissions.SAFE_METHODS \
            and (
                can_user_read_unix_accounts(
                    request.user.provider_username
                )
                or has_user_one_unix_account(
                    request.user.provider_username
                )
            )
        # when managing will be requested
        # return \
        #     request.method in permissions.SAFE_METHODS \
        #     or can_user_manage_unix_accounts(
        #         request.user.provider_username
        #     )

    def has_object_permission(self, request, view, obj):
        if not user_is_authenticated(request.user):
            return False
        if request.method in permissions.SAFE_METHODS:
            return \
                can_user_read_unix_accounts(request.user) \
                or is_user_owner_of_unix_account(
                    request.user.provider_username, obj
                )
        else:
            return False
            # when managing will be requested
            # can_user_manage_unix_accounts(request.user.provider_username)
