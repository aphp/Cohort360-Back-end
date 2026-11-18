import logging
from dataclasses import dataclass
from datetime import timedelta
from typing import Iterable, Optional
from urllib.parse import quote

import requests
from django.conf import settings
from django.core.cache import cache
from django.db.models import Q
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import APIException

from accesses.models import Access, Perimeter, Role
from admin_cohort.http_timeout import HTTP_REQUEST_TIMEOUT
from admin_cohort.models import User

logger = logging.getLogger(__name__)

PORTHAB_ROLE_NAME = "Port'Hab"
RIGHTS_BY_SLUG: dict[str, tuple[str, ...]] = {
    "FULL_ADMIN": ("right_full_admin",),
    "MANAGE_USERS": ("right_manage_users",),
    "MANAGE_DATALABS": ("right_manage_datalabs",),
    "READ_DATALABS": ("right_read_datalabs",),
    "SEARCH_IPP": ("right_search_patients_by_ipp",),
    "SEARCH_OPPOSED": ("right_search_opposed_patients",),
    "EXPORT_CSV": ("right_export_csv_xlsx_nominative",),
    "EXPORT_JUPYTER": ("right_export_jupyter_nominative", "right_export_jupyter_pseudonymized"),
}
RIGHTS_BY_CODE = {f"cohort.{slug.lower()}": rights for slug, rights in RIGHTS_BY_SLUG.items()}
# Seuls ces droits forment le rôle Port'Hab ; les droits de données s'appliquent aux périmètres lus.
MANAGEMENT_RIGHTS = frozenset({"right_full_admin", "right_manage_users", "right_manage_datalabs", "right_read_datalabs"})
PERIMETER_TYPES_BY_PREFIX = {
    "APHP": "AP-HP",
    "GHU": "GHU",
    "GH": "Groupe hospitalier (GH)",
    "H": "Hôpital",
    "POLE": "Pôle/DMU",
    "UF": "Unité Fonctionnelle (UF)",
}
MODES = ("N", "P")
SERVICE_ACCESS_CACHE_KEY = "porthab:service_access"


@dataclass(frozen=True)
class PorthabGrants:
    rights: frozenset[str]
    data_scopes: frozenset[str]


class PorthabUnavailable(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "Les droits Port'Hab sont indisponibles."
    default_code = "porthab_unavailable"


def rights_from_groups(groups: Iterable[str]) -> frozenset[str]:
    prefix = f"BBS_DA-N-{settings.PORTHAB_GROUP_PREFIX}_APP_COHORT_"
    rights: set[str] = set()
    for group in groups:
        name = group.rsplit("/", 1)[-1]
        if name.startswith(prefix) and name[len(prefix) :] in RIGHTS_BY_SLUG:
            rights.update(RIGHTS_BY_SLUG[name[len(prefix) :]])
    return frozenset(rights)


def _is_data_scope(code: str) -> bool:
    identifier, _, mode = code.rpartition("_")
    prefix = identifier.split("_", 1)[0]
    if mode not in MODES or prefix not in PERIMETER_TYPES_BY_PREFIX:
        return False
    return identifier == "APHP" if prefix == "APHP" else "_" in identifier


def data_scopes_from_groups(groups: Iterable[str]) -> frozenset[str]:
    prefix = f"BBS_DA-N-{settings.PORTHAB_GROUP_PREFIX}_PER_"
    names = (group.rsplit("/", 1)[-1] for group in groups)
    return frozenset(name[len(prefix) :] for name in names if name.startswith(prefix) and _is_data_scope(name[len(prefix) :]))


def apply_grants(user: User, grants: PorthabGrants) -> User:
    user.porthab_rights = grants.rights  # type: ignore[attr-defined]
    user.porthab_data_scopes = grants.data_scopes  # type: ignore[attr-defined]
    return user


def porthab_rights(user: User) -> frozenset[str]:
    return getattr(user, "porthab_rights", frozenset())


def porthab_data_scopes(user: User) -> frozenset[str]:
    return getattr(user, "porthab_data_scopes", frozenset())


def porthab_read_perimeter_ids(user: User) -> tuple[frozenset[int], frozenset[int]]:
    """Périmètres lus en nominatif puis en pseudonymisé, d'après les périmètres Port'Hab de l'agent."""
    codes = porthab_data_scopes(user)
    if not codes:
        return frozenset(), frozenset()
    cached = getattr(user, "_porthab_perimeter_ids", None)
    if cached is not None and cached[0] == codes:
        return cached[1]
    wanted: dict[tuple[str, str], set[str]] = {}
    for code in codes:
        identifier, _, mode = code.rpartition("_")
        prefix, _, source_value = identifier.partition("_")
        wanted.setdefault((PERIMETER_TYPES_BY_PREFIX[prefix], source_value or prefix), set()).add(mode)
    query = Q()
    for type_source_value, source_value in wanted:
        query |= Q(type_source_value=type_source_value, source_value=source_value)
    nomi: set[int] = set()
    pseudo: set[int] = set()
    for perimeter_id, type_source_value, source_value in Perimeter.objects.filter(query).values_list("id", "type_source_value", "source_value"):
        modes = wanted[(type_source_value, source_value)]
        if "N" in modes:
            nomi.add(perimeter_id)
        if "P" in modes:
            pseudo.add(perimeter_id)
    result = frozenset(nomi), frozenset(pseudo)
    user._porthab_perimeter_ids = (codes, result)  # type: ignore[attr-defined]
    return result


def porthab_role(user: User) -> Optional[Role]:
    rights = porthab_rights(user) & MANAGEMENT_RIGHTS
    if not rights:
        return None
    return Role(name=PORTHAB_ROLE_NAME, **dict.fromkeys(rights, True))


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
    token = cache.get(SERVICE_ACCESS_CACHE_KEY)
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
    cache.set(SERVICE_ACCESS_CACHE_KEY, payload["access_token"], timeout=max(int(payload.get("expires_in", 60)) - 30, 1))
    return str(payload["access_token"])


def fetch_porthab_grants(username: str) -> PorthabGrants:
    url = f"{settings.PORTHAB_API_URL.rstrip('/')}/api/v1/applications/agents/{quote(username, safe='')}/rights/"
    try:
        response = requests.get(url, headers={"Authorization": f"Bearer {service_token()}"}, timeout=HTTP_REQUEST_TIMEOUT)
    except requests.RequestException as exc:
        logger.exception(f"Port'Hab injoignable pour les droits de {username} : {exc}")
        raise PorthabUnavailable() from exc
    if response.status_code == status.HTTP_401_UNAUTHORIZED:
        cache.delete(SERVICE_ACCESS_CACHE_KEY)
    if response.status_code != status.HTTP_200_OK:
        logger.error(f"Port'Hab a répondu {response.status_code} pour les droits de {username}")
        raise PorthabUnavailable()
    try:
        payload = response.json()
        rights = frozenset(right for code in payload["rights"] if code in RIGHTS_BY_CODE for right in RIGHTS_BY_CODE[code])
        data_scopes = frozenset(code for code in payload.get("data_scopes") or [] if _is_data_scope(code))
    except (ValueError, KeyError, TypeError) as exc:
        logger.error(f"Réponse Port'Hab illisible pour les droits de {username} : {exc}")
        raise PorthabUnavailable() from exc
    return PorthabGrants(rights=rights, data_scopes=data_scopes)
