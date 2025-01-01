from typing import Optional

from rest_framework.permissions import IsAuthenticated, SAFE_METHODS
from rest_framework.exceptions import PermissionDenied

from accesses.permissions import can_user_make_export_jupyter_nomi, can_user_make_export_jupyter_pseudo, \
                                 can_user_read_datalabs, can_user_manage_datalabs, can_user_make_export_csv_nomi, \
                                 can_user_make_export_csv_pseudo
from exports.apps import ExportsConfig

ExportTypes = ExportsConfig.ExportTypes


def check_allow_nomi_export(user, output_format: ExportTypes) -> Optional[bool]:
    if output_format in (ExportTypes.CSV, ExportTypes.XLSX) and not can_user_make_export_csv_nomi(user):
        raise PermissionDenied("Vous n'avez pas le droit d'export CSV/Excel nominatif")
    if output_format == ExportTypes.HIVE and not can_user_make_export_jupyter_nomi(user):
        raise PermissionDenied("Vous n'avez pas le droit d'export Jupyter nominatif")
    return True


def check_allow_pseudo_export(user, output_format: ExportTypes) -> Optional[bool]:
    if output_format in (ExportTypes.CSV, ExportTypes.XLSX) and not can_user_make_export_csv_pseudo(user):
        raise PermissionDenied("Vous n'avez pas le droit d'export CSV pseudonymisé")
    if output_format == ExportTypes.HIVE and not can_user_make_export_jupyter_pseudo(user):
        raise PermissionDenied("Vous n'avez pas le droit d'export Jupyter pseudonymisé")
    return True


class ExportPermission(IsAuthenticated):
    def has_permission(self, request, view):
        authenticated = super().has_permission(request, view)
        if authenticated and request.method == "POST":
            if request.data.get('nominative', False):
                return check_allow_nomi_export(request.user, request.data.get('output_format'))
            else:
                return check_allow_pseudo_export(request.user, request.data.get('output_format'))
        return authenticated

    def has_object_permission(self, request, view, obj):
        return obj.owner == request.user and request.method in SAFE_METHODS


class ReadDatalabsPermission(IsAuthenticated):
    def has_permission(self, request, view):
        authenticated = super().has_permission(request, view)
        return authenticated and can_user_read_datalabs(user=request.user)


class ManageDatalabsPermission(ReadDatalabsPermission):
    def has_permission(self, request, view):
        can_read_datalabs = super().has_permission(request, view)
        return can_read_datalabs and can_user_manage_datalabs(user=request.user)
