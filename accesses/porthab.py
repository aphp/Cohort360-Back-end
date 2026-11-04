import logging
from datetime import timedelta
from typing import Iterable, Optional
from urllib.parse import quote

import requests
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import APIException

from accesses.models import Access, Perimeter, Role
from admin_cohort.http_timeout import HTTP_REQUEST_TIMEOUT
from admin_cohort.models import User

logger = logging.getLogger(__name__)

PORTHAB_ROLE_NAME = "Port'Hab"
RIGHTS_BY_SLUG = {
    "FULL_ADMIN": "right_full_admin",
    "MANAGE_USERS": "right_manage_users",
    "MANAGE_DATALABS": "right_manage_datalabs",
    "READ_DATALABS": "right_read_datalabs",
}
RIGHTS_BY_CODE = {f"cohort.{slug.lower()}": right for slug, right in RIGHTS_BY_SLUG.items()}
SERVICE_TOKEN_CACHE_KEY = "porthab:service_token"


class PorthabUnavailable(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "Les droits Port'Hab sont indisponibles."
    default_code = "porthab_unavailable"


def rights_from_groups(groups: Iterable[str]) -> frozenset[str]:
    prefix = f"BBS_DA-N-{settings.PORTHAB_GROUP_PREFIX}_APP_COHORT_"
    rights = set()
    for group in groups:
        name = group.rsplit("/", 1)[-1]
        if name.startswith(prefix) and name[len(prefix) :] in RIGHTS_BY_SLUG:
            rights.add(RIGHTS_BY_SLUG[name[len(prefix) :]])
    return frozenset(rights)


def porthab_rights(user: User) -> frozenset[str]:
    return getattr(user, "porthab_rights", frozenset())


def porthab_role(user: User) -> Optional[Role]:
    rights = porthab_rights(user)
    if not rights:
        return None
    return Role(name=PORTHAB_ROLE_NAME, **{right: True for right in rights})


def porthab_access(user: User) -> Optional[Access]:
    role = porthab_role(user)
    if role is None:
        return None
    now = timezone.now()
    access = Access(
        role=role,
        perimeter=Perimeter.objects.filter(pk=settings.ROOT_PERIMETER_ID).first(),
        source=PORTHAB_ROLE_NAME,
        start_datetime=now,
        end_datetime=now + timedelta(seconds=settings.SESSION_COOKIE_AGE),
    )
    access.editable = False  # type: ignore[attr-defined]
    return access


def service_token() -> str:
    token = cache.get(SERVICE_TOKEN_CACHE_KEY)
    if token:
        return str(token)
    data = {
        "grant_type": "client_credentials",
        "client_id": settings.PORTHAB_SERVICE_CLIENT_ID,
        "client_secret": settings.PORTHAB_SERVICE_CLIENT_SECRET,
    }
    response = requests.post(settings.PORTHAB_SERVICE_TOKEN_URL, data=data, timeout=HTTP_REQUEST_TIMEOUT)
    if response.status_code != status.HTTP_200_OK:
        raise PorthabUnavailable()
    payload = response.json()
    cache.set(SERVICE_TOKEN_CACHE_KEY, payload["access_token"], timeout=max(int(payload.get("expires_in", 60)) - 30, 1))
    return str(payload["access_token"])


def fetch_porthab_rights(username: str) -> frozenset[str]:
    url = f"{settings.PORTHAB_API_URL.rstrip('/')}/api/v1/applications/agents/{quote(username, safe='')}/rights/"
    try:
        response = requests.get(url, headers={"Authorization": f"Bearer {service_token()}"}, timeout=HTTP_REQUEST_TIMEOUT)
    except requests.RequestException as exc:
        logger.error(f"Port'Hab injoignable pour les droits de {username} : {exc}")
        raise PorthabUnavailable() from exc
    if response.status_code != status.HTTP_200_OK:
        logger.error(f"Port'Hab a répondu {response.status_code} pour les droits de {username}")
        raise PorthabUnavailable()
    return frozenset(RIGHTS_BY_CODE[code] for code in response.json()["rights"] if code in RIGHTS_BY_CODE)
