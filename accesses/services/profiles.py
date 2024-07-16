import logging
from typing import Optional, Dict

from django.core.exceptions import PermissionDenied

from accesses.services.accesses import accesses_service
from admin_cohort.models import User
from admin_cohort.services.auth import auth_service


IMPERSONATING_HEADER = "X-Impersonate"

_logger = logging.getLogger("django.request")


class ProfilesService:

    def __init__(self):
        auth_service.add_post_authentication_hook(ProfilesService.impersonate)

    @staticmethod
    def impersonate(user: User, token: str, headers: Dict[str, str]) -> Optional[User]:
        if IMPERSONATING_HEADER in headers:
            if accesses_service.user_is_full_admin(user):
                impersonated = headers[IMPERSONATING_HEADER]
                try:
                    return User.objects.get(username=impersonated)
                except User.DoesNotExist:
                    _logger.warning(f"Failed to impersonate inexistent user {impersonated}")
                    return user
            else:
                raise PermissionDenied("Vous n'avez pas le droit d'impersonnifier un autre utilisateur")
        return user


profiles_service = ProfilesService()
