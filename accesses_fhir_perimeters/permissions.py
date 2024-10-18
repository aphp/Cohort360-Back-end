from rest_framework.permissions import IsAuthenticated

from accesses.services.accesses import accesses_service
from cohort_job_server.apps import CohortJobServerConfig


class FhirPerimeterResultPermission(IsAuthenticated):
    def has_permission(self, request, view):
        authenticated = super().has_permission(request, view)
        user = request.user
        return authenticated and (accesses_service.user_is_full_admin(user) or
                                  user.username in CohortJobServerConfig.APPLICATIVE_USERS)
