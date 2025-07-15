from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Set

from django.db.models import QuerySet
from django.utils import timezone
from django.conf import settings
from fhirpy import SyncFHIRClient

from accesses.models import Perimeter, Access
from accesses.services.accesses import AccessesService
from accesses_fhir_perimeters.apps import AccessesFhirAuxConfig
from admin_cohort.tools.cache import invalidate_cache

_logger = logging.getLogger("info")
_logger_err = logging.getLogger("django.request")

env = os.environ


@dataclass
class FhirOrganization:
    id: int
    name: str
    part_of: Optional[int] = None
    children: List[FhirOrganization] = field(default_factory=list)


def get_organization_care_sites():
    """
    Fetch all care sites from FHIR Organizations
    """
    auth = None
    if AccessesFhirAuxConfig.FHIR_ACCESS_TOKEN:
        auth = f"Bearer {AccessesFhirAuxConfig.FHIR_ACCESS_TOKEN}"
    client = SyncFHIRClient(AccessesFhirAuxConfig.FHIR_URL, authorization=auth)
    resources = client.resources("Organization")
    resources = resources.search(active=True)
    return {
        int(org.id): FhirOrganization(
            id=int(org.id),
            name=org.name,
            part_of=int(org.get_by_path("partOf.reference")) if org.get_by_path("partOf.reference") else None,
        )
        for org in resources.fetch_all()
    }


def build_tree(all_valid_care_sites: Dict[int, FhirOrganization], main_root_default: FhirOrganization) -> List[
    FhirOrganization]:
    """
    Build a tree of CareSite objects with parent/child relation using part-of attribute from FHIR
    """
    roots = []
    for care_site in all_valid_care_sites.values():
        if care_site.part_of is None:
            roots.append(care_site)
        else:
            parent = all_valid_care_sites.get(care_site.part_of)
            if parent:
                parent.children.append(care_site)
            else:
                _logger.warning(f"Parent {care_site.part_of} not found for {care_site.id}")
                roots.append(care_site)
    if len(roots) > 1:
        main_root_default.children = roots
        return [main_root_default]
    return roots


def get_source_type(care_site: FhirOrganization, level: int) -> str:
    """
    Get the source type for a care site
    TODO: add mapping from the FhirResource to the source type
    """
    if level == 1:
        return settings.ROOT_PERIMETER_TYPE
    if len(settings.PERIMETER_TYPES) >= level:
        return settings.PERIMETER_TYPES[level - 1]
    return get_source_type(care_site, level - 1)


def care_site_to_perimeter(care_site: FhirOrganization, level: int, ancestry: List[FhirOrganization]):
    """
    Convert a care site to a perimeter object
    """

    return Perimeter(
        id=care_site.id,
        local_id=str(care_site.id),
        source_value=None,
        name=care_site.name,
        short_name=care_site.name,
        type_source_value=get_source_type(care_site, level),
        parent_id=ancestry[-1].id if ancestry else None,
        above_levels_ids=",".join([str(ancestor.id) for ancestor in ancestry]),
        inferior_levels_ids=",".join([str(child.id) for child in care_site.children]),
        full_path="/".join([ancestor.name for ancestor in ancestry] + [care_site.name]),
        level=level
    )


def update_perimeter(perimeter: Perimeter, cohort_id: str, cohort_size: int):
    """
    Update a perimeter with new cohort_id and cohort_size
    """
    _logger.info("Updating perimeter %s with cohort_id %s and cohort_size %s", perimeter.id, cohort_id, cohort_size)
    perimeter.cohort_id = cohort_id
    perimeter.cohort_size = cohort_size
    perimeter.save()


def recursively_create_child_perimeters(care_sites: List[FhirOrganization], existing_perimeters: List[Perimeter],
                                        previous_level_perimeters: List[FhirOrganization], level) -> (
List[Perimeter], List[Perimeter]):
    """
    create perimeter from care_sites (skipping existing)
    create virtual cohort from care_sites using the filter fhir : Encounter?service-provider=care_site_id
    update existing perimeter virtual cohort with new virtual cohort data and remove the new virtual cohort
    (this allows to keep the same virtual cohort id that are used in cohort queries)
    TODO: just update the caresite with new Encounter/Patient that doesn't already exist in the List
    """
    existing_perimeters_ids = [perimeter.id for perimeter in existing_perimeters]
    perimeters_to_update = []
    perimeters_to_create = []
    for care_site in care_sites:
        perimeter = care_site_to_perimeter(care_site, level, previous_level_perimeters)
        if care_site.id in existing_perimeters_ids:
            perimeter.cohort_id = existing_perimeters[existing_perimeters_ids.index(care_site.id)].cohort_id
            perimeters_to_update.append(perimeter)
        else:
            perimeters_to_create.append(perimeter)

        child_perimeters_to_create, child_perimeter_to_update = recursively_create_child_perimeters(care_site.children,
                                                                                                    existing_perimeters,
                                                                                                    previous_level_perimeters + [
                                                                                                        care_site],
                                                                                                    level + 1)
        perimeters_to_create.extend(child_perimeters_to_create)
        perimeters_to_update.extend(child_perimeter_to_update)
    if level == 1:
        Perimeter.objects.bulk_create(perimeters_to_create)
        Perimeter.objects.bulk_update(perimeters_to_update,
                                      ["source_value", "name", "short_name", "type_source_value", "parent_id",
                                       "above_levels_ids", "full_path", "inferior_levels_ids", "delete_datetime"])

    return perimeters_to_create, perimeters_to_update


def delete_perimeters(perimeters: QuerySet, care_sites: List[FhirOrganization]) -> QuerySet:
    care_sites_ids = [care_site.id for care_site in care_sites]
    perimeters_to_delete = perimeters.exclude(id__in=care_sites_ids)
    perimeters_to_delete.update(delete_datetime=timezone.now())
    Perimeter.objects.bulk_update(perimeters_to_delete, ['delete_datetime'])
    return perimeters_to_delete


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
            _logger.info(f"Updating virtual cohort {perimeter.cohort_id} for perimeter {perimeter.id}")
            create_virtual_cohort.s(str(perimeter.id), children_ids, int(perimeter.cohort_id)).apply_async()
        else:
            _logger.info(f"Creating virtual cohort for perimeter {perimeter.id}")
            create_virtual_cohort.s(str(perimeter.id), children_ids).apply_async()


def perimeters_data_model_objects_update():
    _logger.info("1. Get All care sites from FHIR")
    all_valid_care_sites = get_organization_care_sites()
    care_sites_tree = build_tree(all_valid_care_sites, main_root_default=FhirOrganization(id=1, name="All Hospitals"))
    _logger.info(f"2. All care sites: {len(all_valid_care_sites)}")
    all_perimeters = Perimeter.objects.all(even_deleted=True)
    _logger.info(f"3. All perimeters: {len(all_perimeters)}")

    _logger.info("4. Create top hierarchy perimeter")
    _logger.info("5. Start recursive Perimeter objects creation")
    perimeter_to_create, perimeter_to_update = recursively_create_child_perimeters(
        care_sites=care_sites_tree,
        existing_perimeters=all_perimeters,
        previous_level_perimeters=[],
        level=1)
    _logger.info(f"6. Creating/Updating new virtual cohorts for perimeters {len(perimeter_to_create)}")
    create_virtual_cohorts(perimeter_to_create, perimeter_to_update)
    _logger.info("7. Deleting removed perimeters")
    perimeters_to_delete = delete_perimeters(perimeters=all_perimeters,
                                             care_sites=list(all_valid_care_sites.values()) + care_sites_tree)
    _logger.info("8. Closing linked accesses")
    AccessesService.close_accesses(perimeters_to_delete)
    _logger.info("End of perimeters updating. Invalidating cache for Perimeters and Accesses")
    invalidate_cache(model_name=Perimeter.__name__)
    invalidate_cache(model_name=Access.__name__)
