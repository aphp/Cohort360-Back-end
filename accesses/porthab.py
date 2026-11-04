from datetime import timedelta
from typing import Iterable, Optional

from django.conf import settings
from django.utils import timezone

from accesses.models import Access, Perimeter, Role
from admin_cohort.models import User

PORTHAB_ROLE_NAME = "Port'Hab"
RIGHTS_BY_SLUG = {
    "FULL_ADMIN": "right_full_admin",
    "MANAGE_USERS": "right_manage_users",
    "MANAGE_DATALABS": "right_manage_datalabs",
    "READ_DATALABS": "right_read_datalabs",
}


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
