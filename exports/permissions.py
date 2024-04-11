from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied

from accesses.permissions import can_user_make_export_jupyter_nomi, can_user_make_export_jupyter_pseudo, can_user_make_csv_export, \
    can_user_make_jupyter_export, can_user_read_datalabs, can_user_manage_datalabs, can_user_make_export_csv_nomi, can_user_make_export_csv_pseudo
from admin_cohort.permissions import user_is_authenticated
from exports import ExportTypes


class ExportRequestsPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method == "POST":
            if request.data.get('nominative', False):
                if request.data.get('output_format') == ExportTypes.CSV and not can_user_make_export_csv_nomi(request.user):
                    raise PermissionDenied("Vous n'avez pas le droit d'export CSV nominatif")
                if request.data.get('output_format') == ExportTypes.HIVE and not can_user_make_export_jupyter_nomi(request.user):
                    raise PermissionDenied("Vous n'avez pas le droit d'export Jupyter nominatif")
            else:
                if request.data.get('output_format') == ExportTypes.CSV and not can_user_make_export_csv_pseudo(request.user):
                    raise PermissionDenied("Vous n'avez pas le droit d'export CSV pseudonymisé")
                if request.data.get('output_format') == ExportTypes.HIVE and not can_user_make_export_jupyter_pseudo(request.user):
                    raise PermissionDenied("Vous n'avez pas le droit d'export Jupyter pseudonymisé")
        return user_is_authenticated(request.user)

    def has_object_permission(self, request, view, obj):
        return user_is_authenticated(request.user) \
               and obj.owner_id == request.user.username \
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
