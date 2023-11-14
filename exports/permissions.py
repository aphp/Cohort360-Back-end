from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied

from admin_cohort.models import User
from admin_cohort.permissions import user_is_authenticated
from accesses.tools import get_bound_roles
from exports.types import ExportType


def can_user_make_export_jupyter_nomi(user: User):
    return any(filter(lambda role: role.right_export_jupyter_nominative, get_bound_roles(user)))


def can_user_make_export_jupyter_pseudo(user: User):
    return any(filter(lambda role: role.right_export_jupyter_pseudonymized, get_bound_roles(user)))


def can_user_make_csv_export(user: User) -> bool:
    return any(filter(lambda role: role.right_export_csv_nominative or role.right_export_csv_pseudonymized, get_bound_roles(user)))


def can_user_make_jupyter_export(user: User) -> bool:
    return any(filter(lambda role: role.right_export_jupyter_nominative or role.right_export_jupyter_pseudonymized, get_bound_roles(user)))


class ExportRequestsPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method == "POST":
            if request.data.get('nominative', False):
                if not can_user_make_export_jupyter_nomi(request.user):
                    raise PermissionDenied("Vous n'êtes autorisé à faire des exports Jupyter en mode nominatif")
            else:
                if not can_user_make_export_jupyter_pseudo(request.user):
                    raise PermissionDenied("Vous n'êtes autorisé à faire des exports Jupyter en mode pseudonymisé")

            if request.data.get('output_format') == ExportType.HIVE:
                owner_id = request.data.get('owner', request.data.get('provider_source_value', request.user.pk))
                if request.user.pk != owner_id:
                    return False
        return user_is_authenticated(request.user)

    def has_object_permission(self, request, view, obj):
        return user_is_authenticated(request.user) \
               and obj.owner_id == request.user.provider_username \
               and request.method in permissions.SAFE_METHODS


class ReadDatalabsPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        return user_is_authenticated(request.user) \
            and can_user_read_datalabs(user=request.user)

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)


class ManageDatalabsPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        return user_is_authenticated(request.user) \
            and can_user_read_datalabs(user=request.user) \
            and can_user_manage_datalabs(user=request.user)


class CSVExportsPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        return user_is_authenticated(request.user) \
            and can_user_make_csv_export(user=request.user)

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)


class JupyterExportPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        return user_is_authenticated(request.user) \
            and can_user_make_jupyter_export(user=request.user)

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)


# WORKSPACES
def can_user_read_datalabs(user: User) -> bool:
    return any(filter(lambda role: role.right_read_datalabs, get_bound_roles(user)))


def can_user_manage_datalabs(user: User) -> bool:
    return any(filter(lambda role: role.right_manage_datalabs, get_bound_roles(user)))
