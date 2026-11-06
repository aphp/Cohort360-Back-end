import logging
from typing import Dict, Optional

from django.conf import settings
from rest_framework.exceptions import PermissionDenied

from accesses.porthab import PorthabUnavailable, fetch_porthab_rights
from accesses.services.accesses import accesses_service
from admin_cohort.models import User


logger = logging.getLogger(__name__)


def impersonate_hook(user: User, headers: Dict[str, str]) -> Optional[User]:
    if settings.IMPERSONATING_HEADER in headers:
        if accesses_service.user_is_full_admin(user):
            impersonated = headers[settings.IMPERSONATING_HEADER]
            try:
                impersonated_user = User.objects.get(username=impersonated)
            except User.DoesNotExist:
                logger.warning(f"Failed to impersonate inexistent user {impersonated}")
                return user
            if settings.PORTHAB_RIGHTS_ENABLED:
                try:
                    impersonated_user.porthab_rights = fetch_porthab_rights(impersonated_user.username)
                except PorthabUnavailable:
                    impersonated_user.porthab_rights = frozenset()
                    logger.warning(f"Droits Port'Hab de {impersonated} indisponibles, impersonation avec ses seuls accès natifs")
            return impersonated_user
        else:
            raise PermissionDenied("Vous n'avez pas le droit d'impersonnifier un autre utilisateur")
    return user
