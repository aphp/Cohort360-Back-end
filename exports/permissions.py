from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied

from admin_cohort.models import User
from admin_cohort.permissions import user_is_authenticated, get_bound_roles
from exports.models import ExportType


def can_export_psql_nomi(user: User):
    return any([r.right_transfer_jupyter_nominative
                for r in get_bound_roles(user)])


def can_export_psql_pseudo(user: User):
    return any([r.right_transfer_jupyter_pseudo_anonymised
                for r in get_bound_roles(user)])


def can_review_transfer_jupyter(user: User):
    """
    Will check the accesses of the Provider,
    Retrieve the roles bound to those,
    And return True if one of these roles
    allow to review jypyter export requests
    @param user:
    @type user: User
    @return: if user can manage at least one type of accesses
    @rtype: bool
    """
    return any([
        r.right_review_transfer_jupyter for r in get_bound_roles(user)
    ])


def can_review_export_csv(user: User):
    """
    Will check the accesses of the Provider,
    Retrieve the roles bound to those,
    And return True if one of these roles allow to review export_csv requests
    @param user:
    @type user: User
    @return: if user can manage at least one type of accesses
    @rtype: bool
    """
    return any([r.right_review_export_csv for r in get_bound_roles(user)])


class ExportJupyterPermissions(permissions.BasePermission):
    message = "Cannot create a non-CSV export request for another user " \
              "without an access with right_review_transfer_jupyter."

    def has_permission(self, request, view):
        output_format = request.data.get('output_format', None)

        if output_format != ExportType.CSV:
            if request.method == "POST":
                owner_id = request.data.get(
                    'owner', request.data.get(
                        'provider_source_value', request.user.pk))

                if request.user.pk != owner_id:
                    if not can_review_transfer_jupyter(request.user):
                        return False
        return True


class ExportRequestPermissions(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method == "POST":
            if request.data.get('nominative', False):
                if not can_export_psql_nomi(request.user):
                    raise PermissionDenied(
                        "L'utilisateur destinataire n'a pas le "
                        "droit d'export nominatif")
            else:
                if not can_export_psql_pseudo(request.user):
                    raise PermissionDenied(
                        "L'utilisateur destinataire n'a pas le "
                        "droit d'export pseudonymisé")

        return user_is_authenticated(request.user)

    def has_object_permission(self, request, view, obj):
        # todo : doublecheck
        return user_is_authenticated(request.user) \
               and obj.provider_id == request.user.provider_id \
               and request.method in permissions.SAFE_METHODS


class AnnexesPermissions(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.method == "GET" \
               and user_is_authenticated(request.user) and \
               (can_review_transfer_jupyter(request.user)
                or can_review_export_csv(request.user))

    def has_object_permission(self, request, view, obj):
        return user_is_authenticated(request.user) \
               and obj.provider_id == request.user.provider_username \
               and request.method in permissions.SAFE_METHODS
