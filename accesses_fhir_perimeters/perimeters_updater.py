from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Set, Tuple

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from fhirpy import SyncFHIRClient
from fhirpy.base.exceptions import OperationOutcome

from accesses.models import Perimeter, Access
from accesses.services.accesses import AccessesService
from accesses_fhir_perimeters.apps import AccessesFhirAuxConfig
from admin_cohort.services.auth import jwt_auth_service
from admin_cohort.tools.cache import invalidate_cache

logger = logging.getLogger(__name__)

FHIR_PAGE_SIZE = 1000

SYNCED_FIELDS = [
    "source_value",
    "name",
    "short_name",
    "type_source_value",
    "parent_id",
    "above_levels_ids",
    "full_path",
    "inferior_levels_ids",
    "level",
    "delete_datetime",
]


class PerimetersSyncAborted(Exception):
    pass


@dataclass
class FhirOrganization:
    id: int
    name: str
    part_of: Optional[int] = None
    source_value: Optional[str] = None
    type_source_value: Optional[str] = None
    children: List[FhirOrganization] = field(default_factory=list)


@dataclass
class PerimetersSyncResult:
    to_create: List[Perimeter]
    to_update: List[Perimeter]
    to_delete_ids: List[int]
    reactivated_ids: List[int]
    orphans_ids: List[int]


def parse_reference_id(reference: Optional[str]) -> Optional[int]:
    """
    Extract the logical id from a FHIR reference ("Organization/123") or a bare id ("123")
    """
    if not reference:
        return None
    return int(str(reference).rsplit("/", 1)[-1])


def get_type_source_value(org) -> Optional[str]:
    """
    Organization.type holds the care site type as a coding code (e.g. "Groupe hospitalier (GH)"),
    next to a govt/prov category coding. Keep the first value that is a known perimeter type.
    """
    for type_ in org.get("type") or []:
        for coding in type_.get("coding") or []:
            for value in (coding.get("code"), coding.get("display")):
                if value in settings.PERIMETER_TYPES:
                    return value
    return None


def to_fhir_organization(org) -> Optional[FhirOrganization]:
    try:
        org_id = parse_reference_id(org.id)
        part_of = parse_reference_id(org.get_by_path("partOf.reference"))
    except ValueError:
        logger.warning(f"Skipping Organization {org.id}: non numeric id or partOf {org.get_by_path('partOf.reference')}")
        return None
    if org_id is None:
        return None
    aliases = org.get("alias") or []
    return FhirOrganization(
        id=org_id,
        name=org.get("name"),
        part_of=part_of,
        source_value=aliases[0] if aliases else None,
        type_source_value=get_type_source_value(org),
    )


def get_fhir_client(force_system_token: bool = False) -> SyncFHIRClient:
    token = AccessesFhirAuxConfig.FHIR_ACCESS_TOKEN
    if force_system_token or not token:
        token = jwt_auth_service.generate_system_token()
    return SyncFHIRClient(AccessesFhirAuxConfig.FHIR_URL or "", authorization=f"Bearer {token}")


def fetch_organizations(client: SyncFHIRClient) -> list:
    return list(client.resources("Organization").search(active=True).limit(FHIR_PAGE_SIZE).fetch_all())


def get_organization_care_sites() -> Dict[int, FhirOrganization]:
    """
    Fetch all active FHIR Organizations whose type is one of settings.PERIMETER_TYPES
    """
    start = time.monotonic()
    try:
        organizations = fetch_organizations(get_fhir_client())
    except OperationOutcome as e:
        # the system token is short-lived: retry once with a fresh one
        logger.warning(f"Fetching Organizations failed ({e}), retrying with a new system token")
        organizations = fetch_organizations(get_fhir_client(force_system_token=True))
    logger.info(f"Fetched {len(organizations)} Organizations from FHIR in {time.monotonic() - start:.1f}s")

    care_sites = {}
    skipped_count = 0
    for org in organizations:
        care_site = to_fhir_organization(org)
        if care_site is None or care_site.type_source_value is None:
            skipped_count += 1
            continue
        care_sites[care_site.id] = care_site
    logger.info(f"Kept {len(care_sites)} Organizations, skipped {skipped_count} (invalid id or type not in PERIMETER_TYPES)")
    return care_sites


def build_tree(all_valid_care_sites: Dict[int, FhirOrganization], root_id: int) -> Tuple[FhirOrganization, List[FhirOrganization]]:
    """
    Build the care site tree under the root, using the partOf relation.
    Returns the root and the orphan care sites (not attached to the root, they are left out of the tree)
    """
    root = all_valid_care_sites.get(root_id)
    if root is None:
        raise PerimetersSyncAborted(f"Root perimeter {root_id} not found among FHIR Organizations")
    for care_site in all_valid_care_sites.values():
        care_site.children = []
    for care_site in all_valid_care_sites.values():
        parent = all_valid_care_sites.get(care_site.part_of) if care_site.part_of is not None else None
        if parent and care_site.id != root_id:
            parent.children.append(care_site)

    attached_ids = set()
    stack = [root]
    while stack:
        care_site = stack.pop()
        if care_site.id in attached_ids:
            continue
        attached_ids.add(care_site.id)
        stack.extend(care_site.children)
    orphans = [cs for cs in all_valid_care_sites.values() if cs.id not in attached_ids]
    return root, orphans


def care_site_label(care_site: FhirOrganization) -> str:
    return f"{care_site.source_value}-{care_site.name}"


def care_site_to_perimeter(care_site: FhirOrganization, level: int, ancestry: List[FhirOrganization]) -> Perimeter:
    """
    Convert a care site to a perimeter object
    """
    return Perimeter(
        id=care_site.id,
        local_id=str(care_site.id),
        source_value=care_site.source_value,
        name=care_site.name,
        short_name=care_site.name,
        type_source_value=care_site.type_source_value,
        parent_id=ancestry[-1].id if ancestry else None,
        above_levels_ids=",".join([str(ancestor.id) for ancestor in ancestry]) or None,
        inferior_levels_ids=",".join([str(child.id) for child in care_site.children]),
        full_path="/".join([care_site_label(ancestor) for ancestor in ancestry] + [care_site_label(care_site)]),
        level=level,
        delete_datetime=None,
    )


def is_perimeter_different(new: Perimeter, existing: Perimeter) -> bool:
    return any(getattr(new, f) != getattr(existing, f) for f in SYNCED_FIELDS)


def update_perimeter(perimeter: Perimeter, cohort_id: str, cohort_size: int):
    """
    Update a perimeter with new cohort_id and cohort_size
    """
    logger.info("Updating perimeter %s with cohort_id %s and cohort_size %s", perimeter.id, cohort_id, cohort_size)
    perimeter.cohort_id = cohort_id
    perimeter.cohort_size = cohort_size
    perimeter.save()


def recursively_create_child_perimeters(
    care_sites: List[FhirOrganization], existing_perimeters: Dict[int, Perimeter], previous_level_perimeters: List[FhirOrganization], level
) -> Tuple[List[Perimeter], List[Perimeter], List[Perimeter]]:
    """
    Map the care sites tree to perimeters, split into (to create, to update, unchanged).
    Existing perimeters keep their cohort_id, those previously deleted are reactivated (delete_datetime=None).
    """
    perimeters_to_create, perimeters_to_update, perimeters_unchanged = [], [], []
    for care_site in care_sites:
        perimeter = care_site_to_perimeter(care_site, level, previous_level_perimeters)
        existing = existing_perimeters.get(care_site.id)
        if existing is None:
            perimeters_to_create.append(perimeter)
        else:
            perimeter.cohort_id = existing.cohort_id
            if is_perimeter_different(perimeter, existing):
                perimeters_to_update.append(perimeter)
            else:
                perimeters_unchanged.append(perimeter)

        to_create, to_update, unchanged = recursively_create_child_perimeters(
            care_site.children, existing_perimeters, previous_level_perimeters + [care_site], level + 1
        )
        perimeters_to_create.extend(to_create)
        perimeters_to_update.extend(to_update)
        perimeters_unchanged.extend(unchanged)
    return perimeters_to_create, perimeters_to_update, perimeters_unchanged


def get_all_children_perimeters(perimeter: Perimeter, all_perimeters: List[Perimeter]) -> Set[str]:
    children = set()
    for p in all_perimeters:
        if p.is_child_of(perimeter):
            children.add(str(p.id))
            children = children.union(get_all_children_perimeters(p, all_perimeters))
    return children


def create_virtual_cohorts(perimeter_to_create: List[Perimeter], perimeter_to_update: List[Perimeter]):
    from accesses_fhir_perimeters.tasks import create_virtual_cohort

    perimeters = perimeter_to_create + perimeter_to_update
    for perimeter in perimeters:
        children_ids = sorted(get_all_children_perimeters(perimeter, perimeters))
        if perimeter.cohort_id:
            logger.info(f"Updating virtual cohort {perimeter.cohort_id} for perimeter {perimeter.id}")
            create_virtual_cohort.s(str(perimeter.id), children_ids, int(perimeter.cohort_id)).apply_async()
        else:
            logger.info(f"Creating virtual cohort for perimeter {perimeter.id}")
            create_virtual_cohort.s(str(perimeter.id), children_ids).apply_async()


def compute_perimeters_sync() -> Tuple[PerimetersSyncResult, List[Perimeter]]:
    """
    Read-only: compute the changes to apply to the Perimeter table from FHIR Organizations.
    Also returns the unchanged perimeters (needed to build the virtual cohorts of the whole tree).
    FHIR is only queried with active=true: an Organization that disappeared is a deleted perimeter.
    Orphans (not attached to the root) are neither created nor deleted.
    """
    all_valid_care_sites = get_organization_care_sites()
    root, orphans = build_tree(all_valid_care_sites, root_id=settings.ROOT_PERIMETER_ID)
    if orphans:
        logger.warning(f"{len(orphans)} Organizations are not attached to the root {root.id}, they are ignored: {[o.id for o in orphans][:50]}")

    existing_perimeters = {p.id: p for p in Perimeter.objects.all(even_deleted=True)}
    to_create, to_update, unchanged = recursively_create_child_perimeters(
        care_sites=[root], existing_perimeters=existing_perimeters, previous_level_perimeters=[], level=1
    )
    to_delete_ids = sorted(p.id for p in existing_perimeters.values() if p.delete_datetime is None and p.id not in all_valid_care_sites)
    reactivated_ids = sorted(p.id for p in to_update if existing_perimeters[p.id].delete_datetime is not None)
    result = PerimetersSyncResult(
        to_create=to_create,
        to_update=to_update,
        to_delete_ids=to_delete_ids,
        reactivated_ids=reactivated_ids,
        orphans_ids=[o.id for o in orphans],
    )
    return result, unchanged


def delete_perimeters(perimeters_ids: List[int]):
    """
    Soft-delete perimeters. Already deleted perimeters are not passed here and keep their delete_datetime.
    """
    Perimeter.objects.all().filter(id__in=perimeters_ids).update(delete_datetime=timezone.now())
    deleted_perimeters = Perimeter.objects.all(even_deleted=True).filter(id__in=perimeters_ids)
    logger.info(f"{len(perimeters_ids)} perimeters have been deleted: {perimeters_ids}")
    return deleted_perimeters


def perimeters_data_model_objects_update():
    logger.info("1. Compute perimeters changes from FHIR Organizations")
    try:
        sync, unchanged = compute_perimeters_sync()
    except PerimetersSyncAborted as e:
        logger.exception(f"Perimeters sync aborted: {e}")
        return
    logger.info(
        f"2. Perimeters to create: {len(sync.to_create)}, to update: {len(sync.to_update)} (reactivated: {len(sync.reactivated_ids)}), "
        f"unchanged: {len(unchanged)}, to delete: {len(sync.to_delete_ids)}, orphans ignored: {len(sync.orphans_ids)}"
    )
    # All or nothing: a perimeter soft-deleted without its accesses closed would never be retried,
    # since the next run only deletes perimeters that are still active.
    with transaction.atomic():
        Perimeter.objects.bulk_create(sync.to_create)
        Perimeter.objects.bulk_update(sync.to_update, SYNCED_FIELDS)
        logger.info("3. Deleting removed perimeters")
        perimeters_to_delete = delete_perimeters(sync.to_delete_ids)
        logger.info("4. Closing linked accesses")
        AccessesService.close_accesses(perimeters_to_delete)

    # After the commit: the cohort callbacks (/fhir-perimeters/<id>/) must find the new perimeters
    logger.info("5. Creating/Updating virtual cohorts for perimeters")
    create_virtual_cohorts(sync.to_create, sync.to_update + unchanged)
    logger.info("End of perimeters updating. Invalidating cache for Perimeters and Accesses")
    invalidate_cache(model_name=Perimeter.__name__)
    invalidate_cache(model_name=Access.__name__)
