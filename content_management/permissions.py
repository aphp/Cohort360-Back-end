from rest_framework.permissions import IsAuthenticated, SAFE_METHODS

from accesses.services.accesses import accesses_service


class ContentManagementPermission(IsAuthenticated):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        authenticated = super().has_permission(request, view)
        user = request.user
        return authenticated and (accesses_service.user_is_full_admin(user))
