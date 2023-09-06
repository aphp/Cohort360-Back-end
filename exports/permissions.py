from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied

from accesses.permissions import can_user_manage_unix_accounts, can_user_read_unix_accounts
from admin_cohort.models import User
from admin_cohort.permissions import user_is_authenticated, get_bound_roles
from exports.types import ExportType


def can_export_jupyter_nomi(user: User):
    return any([r.right_transfer_jupyter_nominative for r in get_bound_roles(user)])


def can_export_jupyter_pseudo(user: User):
    return any([r.right_transfer_jupyter_pseudo_anonymised for r in get_bound_roles(user)])


def can_review_transfer_jupyter(user: User) -> bool:
    return any([r.right_review_transfer_jupyter for r in get_bound_roles(user)])


def can_review_export_csv(user: User) -> bool:
    return any([r.right_review_export_csv for r in get_bound_roles(user)])


def can_review_export(user: User) -> bool:
    return any([r.right_review_export_csv or r.right_review_transfer_jupyter
                for r in get_bound_roles(user)])


class ExportJupyterPermissions(permissions.BasePermission):
    message = "Cannot create a non-CSV export request for another user "\
              "without an access with right_review_transfer_jupyter."

    def has_permission(self, request, view):
        output_format = request.data.get('output_format')

        if request.method == "POST" and output_format != ExportType.CSV:
            owner_id = request.data.get('owner',
                                        request.data.get('provider_source_value', request.user.pk))
            if request.user.pk != owner_id and not can_review_transfer_jupyter(request.user):
                return False
        return True


class ExportRequestPermissions(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method == "POST":
            if request.data.get('nominative', False):
                if not can_export_jupyter_nomi(request.user):
                    raise PermissionDenied("L'utilisateur destinataire n'a pas le droit d'export nominatif")
            else:
                if not can_export_jupyter_pseudo(request.user):
                    raise PermissionDenied("L'utilisateur destinataire n'a pas le droit d'export pseudonymisé")

        return user_is_authenticated(request.user)

    def has_object_permission(self, request, view, obj):
        return user_is_authenticated(request.user) \
               and obj.owner_id == request.user.provider_username \
               and request.method in permissions.SAFE_METHODS


class AnnexesPermissions(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.method == "GET" \
               and user_is_authenticated(request.user) \
               and (can_review_transfer_jupyter(request.user)
                    or can_review_export_csv(request.user))

    def has_object_permission(self, request, view, obj):
        return user_is_authenticated(request.user) \
               and obj.owner_id == request.user.provider_username \
               and request.method in permissions.SAFE_METHODS


class ReadWorkspacesPermissions(permissions.BasePermission):
    def has_permission(self, request, view):
        return user_is_authenticated(request.user) \
            and can_user_read_unix_accounts(user=request.user)

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)


class ManageWorkspacesPermissions(permissions.BasePermission):
    def has_permission(self, request, view):
        return user_is_authenticated(request.user) \
            and can_user_manage_unix_accounts(user=request.user)

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)
