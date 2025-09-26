import logging
from typing import Dict, Optional

from django.conf import settings
from rest_framework.exceptions import PermissionDenied

from accesses.services.accesses import accesses_service
from admin_cohort.models import User


logger = logging.getLogger(__name__)

def impersonate_hook(user: User, headers: Dict[str, str]) -> Optional[User]:
    if settings.IMPERSONATING_HEADER in headers:
        if accesses_service.user_is_full_admin(user):
            impersonated = headers[settings.IMPERSONATING_HEADER]
            try:
                return User.objects.get(username=impersonated)
            except User.DoesNotExist:
                logger.warning(f"Failed to impersonate inexistent user {impersonated}")
                return user
        else:
            raise PermissionDenied("Vous n'avez pas le droit d'impersonnifier un autre utilisateur")
    return user
