from rest_framework.permissions import IsAuthenticated
from cohort_job_server.apps import CohortJobServerConfig

APPLICATIVE_USERS = CohortJobServerConfig.APPLICATIVE_USERS


class AuthenticatedApplicativeUserPermission(IsAuthenticated):
    def has_permission(self, request, view):
        return super().has_permission(request, view) and \
            request.user.username in APPLICATIVE_USERS


class QueryExecutororETLCallbackPermission(AuthenticatedApplicativeUserPermission):
    def has_permission(self, request, view):
        return super().has_permission(request, view) and \
            request.method in ("GET", "PATCH")

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)
