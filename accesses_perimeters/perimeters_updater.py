from __future__ import annotations

import logging
import os
from typing import List, Union

from django.db.models import Q, QuerySet
from django.db.models.query import RawQuerySet
from django.utils import timezone

from accesses.models import Perimeter, Access
from accesses.services.accesses import AccessesService
from accesses_perimeters.models import Concept, CareSite
from admin_cohort import settings
from admin_cohort.tools.cache import invalidate_cache

"""
This script define 3 data models and the function which will refresh by insert/update all modified Perimeters objects.

One Perimeter is built with care site information and the relation with other care site in the hierarchy of services.
In our case, all Perimeters and the service hierarchy are in omop tables. We have to fetch information
from those tables, saved its in data models and apply logical rule to build again all perimeters.

New Data Models:
- Provider: the user object reference. it will be mapped by omop.provider, it contains user information id, name etc...
- CareSite: the medical service reference. it will be mapped by omop.care_site, it contains user information like
  care site id, care site name, type of care site (if it is an hospital lower or bigger service) etc...
- Concept: the translation of reference concept table from omop. It used to get technical id from concept label
  (concept name) to finally apply filter on other table.

Care site Hierarchy: each care site must have a type, which correspond to the "level" of this care site in the hierarchy
It is a mono-hierarchy => one parent maximum for 1.n children

1) With build PSQL Query with Concept result filter, and fetch care_site and relation between them in CareSite objects
2) We generate Perimeters objects ordering by desc in hierarchy logic (from the top level to leafs)
3) We save all perimeters objects in that order
"""

_logger = logging.getLogger("info")
_logger_err = logging.getLogger("django.request")

env = os.environ


class RelationPerimeter:
    def __init__(self, above_levels_ids: Union[str, None], inferior_levels_ids: str, full_path: str, level: int):
        self.above_levels_ids = above_levels_ids
        self.inferior_levels_ids = inferior_levels_ids
        self.full_path = full_path
        self.level = level


def get_concept_filter_id() -> tuple:
    """
    Get technical id from 2 concept of the table omop.fact_relationship:
    - domain_concept_id (1 et 2)
    - relationship_concept_id
    It is used to define the relation between fact_id_1 and fact_id_2 in Where clause in psql query.
    """
    try:
        domain_id = env.get("CARE_SITE_DOMAIN_CONCEPT_NAME")
        relationship_id = env.get("IS_PART_OF_RELATIONSHIP_NAME")
        is_part_of_rel_id = Concept.objects.get(concept_name=relationship_id).concept_id
        cs_domain_concept_id = Concept.objects.get(concept_name=domain_id).concept_id
    except Concept.DoesNotExist as e:
        raise ValueError(f"Error while getting Concepts: {e}")
    return str(is_part_of_rel_id), str(cs_domain_concept_id)


def psql_query_care_site_relationship(top_care_site_id: int) -> str:
    """
    PSQL query to get all filtered care sites with the direct parent associated.
    it uses 2 tables from OMOP PG:  omop.care_site and omop.fact_relationship
    """
    is_part_of_rel_id, cs_domain_concept_id = get_concept_filter_id()
    return f"""
            WITH care_sites AS (
            SELECT
            cs.care_site_id,
            cs.care_site_name,
            cs.care_site_short_name,
            cs.care_site_type_source_value,
            cs.care_site_source_value,
            NULL as care_site_parent_id,
            cd.id as cohort_id,
            cd._size as cohort_size
            FROM omop.care_site cs
            INNER JOIN omop.list cd
            ON cd._sourcereferenceid = CAST(cs.care_site_id as VARCHAR)
            WHERE (cs.care_site_id = {top_care_site_id}
                   AND cs.delete_datetime IS NULL
                   AND cd.delete_datetime IS NULL AND cd.source__type = 'Organization')
            UNION
            SELECT
            css.care_site_id,
            css.care_site_name,
            css.care_site_short_name,
            css.care_site_type_source_value,
            css.care_site_source_value,
            CAST(frr.fact_id_2 AS BIGINT) care_site_parent_id,
            cd.id as cohort_id,
            cd._size as cohort_size
            FROM omop.care_site css
            INNER JOIN omop.fact_relationship frr
            ON css.care_site_id=frr.fact_id_1
            INNER JOIN omop.list cd
            ON cd._sourcereferenceid = cast(css.care_site_id as VARCHAR)
            WHERE (frr.fact_id_1!=frr.fact_id_2
                   AND frr.domain_concept_id_1={cs_domain_concept_id}
                   AND frr.domain_concept_id_2={cs_domain_concept_id}
                   AND frr.relationship_concept_id={is_part_of_rel_id}
                   AND css.care_site_type_source_value IN ({str(settings.PERIMETERS_TYPES)[1:-1]})
                   AND css.delete_datetime IS NULL
                   AND frr.delete_datetime IS NULL
                   AND cd.delete_datetime IS NULL AND cd.source__type = 'Organization')
            )
            SELECT DISTINCT * FROM care_sites;"""


def map_care_site_to_perimeter(care_site: CareSite, relation_perimeter: RelationPerimeter):
    return Perimeter(id=care_site.care_site_id,
                     local_id=str(care_site.care_site_id),
                     source_value=care_site.care_site_source_value,
                     name=care_site.care_site_name,
                     short_name=care_site.care_site_short_name,
                     type_source_value=care_site.care_site_type_source_value,
                     parent_id=care_site.care_site_parent_id,
                     cohort_id=care_site.cohort_id,
                     cohort_size=care_site.cohort_size,
                     above_levels_ids=relation_perimeter.above_levels_ids,
                     inferior_levels_ids=relation_perimeter.inferior_levels_ids,
                     full_path=relation_perimeter.full_path,
                     level=relation_perimeter.level
                     )


def is_care_site_different_from_perimeter(care_site: CareSite, perimeter: Perimeter, relation_perimeter: RelationPerimeter):
    return any((care_site.care_site_parent_id != perimeter.parent_id,
                care_site.care_site_type_source_value != perimeter.type_source_value,
                care_site.care_site_name != perimeter.name,
                care_site.care_site_short_name != perimeter.short_name,
                care_site.delete_datetime != perimeter.delete_datetime,
                str(care_site.cohort_id) != str(perimeter.cohort_id),
                str(care_site.cohort_size) != str(perimeter.cohort_size),
                relation_perimeter.above_levels_ids != perimeter.above_levels_ids,
                relation_perimeter.full_path != perimeter.full_path,
                relation_perimeter.inferior_levels_ids != perimeter.inferior_levels_ids))


def set_perimeters_to_create_and_update(perimeters_to_create: List[Perimeter],
                                        perimeters_to_update: List[Perimeter],
                                        all_perimeters: QuerySet,
                                        care_site: CareSite,
                                        relation_perimeter: RelationPerimeter,
                                        previous_level_perimeters: List[Perimeter]):
    try:
        perimeter = all_perimeters.get(id=care_site.care_site_id)
        if is_care_site_different_from_perimeter(care_site, perimeter, relation_perimeter):
            perimeters_to_update.append(map_care_site_to_perimeter(care_site, relation_perimeter))
        else:
            previous_level_perimeters.append(perimeter)
    except Perimeter.DoesNotExist:
        perimeters_to_create.append(map_care_site_to_perimeter(care_site, relation_perimeter))


def get_parent_perimeter_from_perimeters(perimeters: List[Perimeter], care_site_parent_id: int) -> Perimeter:
    for perimeter in perimeters:
        if perimeter.id == care_site_parent_id:
            return perimeter
    raise ValueError(f"{care_site_parent_id} has no previous perimeters with the same id")


def create_top_perimeter(top_care_site: CareSite, all_care_sites: QuerySet, all_perimeters: QuerySet) -> List[Perimeter]:
    if not all_perimeters:
        all_perimeters = Perimeter.objects.none()

    perimeters_to_create = []
    perimeters_to_update = []
    current_perimeters = []

    path = f"{top_care_site.care_site_source_value}-{top_care_site.care_site_name}"
    _logger.info(f"Top perimeter path: {path}")

    children = get_child_care_sites(care_site=top_care_site,
                                    all_care_sites=all_care_sites)
    top_level = 1
    relation_perimeters = RelationPerimeter(above_levels_ids=None,
                                            inferior_levels_ids=children,
                                            full_path=path,
                                            level=top_level)
    set_perimeters_to_create_and_update(perimeters_to_create=perimeters_to_create,
                                        perimeters_to_update=perimeters_to_update,
                                        all_perimeters=all_perimeters,
                                        care_site=top_care_site,
                                        relation_perimeter=relation_perimeters,
                                        previous_level_perimeters=current_perimeters)
    top_care_site_level = top_care_site.care_site_type_source_value

    _logger.info(f"Process at level: {top_care_site_level} "
                 f"-Current Perimeters: {len(current_perimeters)} "
                 f"-Perimeters to create: {len(perimeters_to_create)} "
                 f"-Perimeters to update: {len(perimeters_to_update)}")

    insert_perimeters(perimeters_to_create)
    update_perimeters(perimeters_to_update)
    return current_perimeters + perimeters_to_create + perimeters_to_update


def recursively_create_child_perimeters(parents_ids: List[int],
                                        care_sites: List[CareSite],
                                        all_perimeters: QuerySet,
                                        previous_level_perimeters: List[Perimeter],
                                        level: int):
    if not all_perimeters:
        all_perimeters = Perimeter.objects.none()

    children_care_site_objects = []
    perimeters_to_create = []
    perimeters_to_update = []
    current_parents_ids = []
    care_site_levels = []
    new_previous_level_list = []
    # for every care_site where id is in current parent id list we map to perimeter and add it to a list
    for care_site in care_sites:
        if care_site.care_site_parent_id in parents_ids:
            if care_site.care_site_id in current_parents_ids:
                _logger.warning(f"Care site {care_site.care_site_id} has 2 or more parents !")
                continue

            # We get the previous above_levels_ids value from parent perimeter and add current id
            parent_perimeter = get_parent_perimeter_from_perimeters(perimeters=previous_level_perimeters,
                                                                    care_site_parent_id=care_site.care_site_parent_id)

            if parent_perimeter.above_levels_ids:
                above_levels_ids = ",".join([parent_perimeter.above_levels_ids, str(parent_perimeter.id)])
            else:
                above_levels_ids = str(parent_perimeter.id)
            children = get_child_care_sites(care_site=care_site, all_care_sites=care_sites)
            full_path = f"{parent_perimeter.full_path}/{care_site.care_site_source_value}-{care_site.care_site_name}"

            relation_perimeter = RelationPerimeter(above_levels_ids=above_levels_ids,
                                                   inferior_levels_ids=children,
                                                   full_path=full_path,
                                                   level=level)

            set_perimeters_to_create_and_update(perimeters_to_create=perimeters_to_create,
                                                perimeters_to_update=perimeters_to_update,
                                                all_perimeters=all_perimeters,
                                                care_site=care_site,
                                                relation_perimeter=relation_perimeter,
                                                previous_level_perimeters=new_previous_level_list)

            current_parents_ids.append(care_site.care_site_id)
            care_site_levels.append(care_site.care_site_type_source_value)
        else:
            children_care_site_objects.append(care_site)

    _logger.info(f"Children care_site objects found: {len(children_care_site_objects)}")

    if perimeters_to_create or perimeters_to_update or new_previous_level_list:
        _logger.info(f"Process at levels: {set(care_site_levels)}\n"
                     f"- Perimeters already existing: {len(new_previous_level_list)}\n"
                     f"- Perimeters to Create: {len(perimeters_to_create)}\n"
                     f"- Perimeters to update: {len(perimeters_to_update)}")
        insert_perimeters(perimeters_to_create)
        update_perimeters(perimeters_to_update)
        new_previous_level_list = new_previous_level_list + perimeters_to_create + perimeters_to_update
        recursively_create_child_perimeters(parents_ids=current_parents_ids,
                                            care_sites=children_care_site_objects,
                                            all_perimeters=all_perimeters,
                                            previous_level_perimeters=new_previous_level_list,
                                            level=level+1)


def update_perimeters(perimeters_to_update: List[Perimeter]):
    Perimeter.objects.bulk_update(perimeters_to_update,
                                  ["source_value", "name", "short_name", "type_source_value", "parent_id",
                                   "above_levels_ids", "full_path", "inferior_levels_ids", "delete_datetime",
                                   "cohort_id", "cohort_size"])


def insert_perimeters(perimeters_to_create: List[Perimeter]):
    Perimeter.objects.bulk_create(perimeters_to_create)


def delete_perimeters(perimeters: QuerySet, care_sites: RawQuerySet):
    perimeters_to_delete = get_perimeters_to_delete(all_perimeters=perimeters,
                                                    all_valid_care_sites=care_sites)
    if perimeters_to_delete:
        update_perimeters(perimeters_to_delete)
        _logger.info(f"{len(perimeters_to_delete)} perimeters have been deleted - {perimeters_to_delete}")
    else:
        _logger.info("No perimeters have been deleted")
    return perimeters_to_delete


def get_perimeters_to_delete(all_perimeters: QuerySet, all_valid_care_sites: RawQuerySet):
    deleted_care_sites = CareSite.objects.raw(CareSite.sql_get_deleted_care_sites())
    deleted_care_sites_ids = (cs.care_site_id for cs in deleted_care_sites)
    valid_care_sites_ids = (cs.care_site_id for cs in all_valid_care_sites)

    perimeters_to_delete_1 = all_perimeters.exclude(id__in=valid_care_sites_ids)
    perimeters_to_delete_2 = all_perimeters.filter(Q(id__in=deleted_care_sites_ids))

    perimeters_to_delete_1.update(delete_datetime=timezone.now())
    _logger.info(f"Perimeters are no longer present in care_site hierarchy: {perimeters_to_delete_1}")

    for perimeter in perimeters_to_delete_2:
        perimeter.delete_datetime = deleted_care_sites.get(care_site_id=perimeter.id).delete_datetime
        _logger.info(f"Perimeter {perimeter.id} was referencing a deleted care_site")
    return perimeters_to_delete_1.union(perimeters_to_delete_2)


def get_child_care_sites(care_site: CareSite, all_care_sites: Union[List[CareSite], QuerySet]) -> str:
    children_ids = (str(cs.care_site_id) for cs in all_care_sites if cs.care_site_parent_id == care_site.care_site_id)
    return ",".join(children_ids)


"""
Main function to recreate all Perimeters:
the update run in "INSERT/UPDATE/DELETE" mode (delta).

process steps:
1) Get list of top care site hierarchy
2) Fetch from OMOP PG tables all needed data to build CareSite object tree
3) Get all existing perimeters
4) Insert or update perimeters with refreshed data
5) Add delete timestamp to deleted perimeters and close accesses with no valid perimeter
"""


def perimeters_data_model_objects_update():
    aphp_id = int(env.get("TOP_HIERARCHY_CARE_SITE_ID"))
    _logger.info("1. Get top hierarchy ID. Must be APHP's")

    all_valid_care_sites = CareSite.objects.raw(psql_query_care_site_relationship(top_care_site_id=aphp_id))
    try:
        top_care_site = [cs for cs in all_valid_care_sites if cs.care_site_id == aphp_id][0]
    except IndexError:
        _logger_err.error("Perimeters daily update: missing top care site APHP")
        return
    _logger.info(f"2. Fetch {len(all_valid_care_sites)} care sites from OMOP DB")

    all_perimeters = Perimeter.objects.all(even_deleted=True)
    _logger.info(f"3. All perimeters: {len(all_perimeters)}")

    _logger.info("4. Create top hierarchy perimeter")
    top_perimeters = create_top_perimeter(top_care_site=top_care_site,
                                          all_care_sites=all_valid_care_sites,
                                          all_perimeters=all_perimeters)
    _logger.info("5. Start recursive Perimeter objects creation")
    second_level = 2
    recursively_create_child_perimeters(parents_ids=[aphp_id],
                                        care_sites=all_valid_care_sites,
                                        all_perimeters=all_perimeters,
                                        previous_level_perimeters=top_perimeters,
                                        level=second_level)
    _logger.info("6. Deleting removed perimeters")
    perimeters_to_delete = delete_perimeters(perimeters=all_perimeters, care_sites=all_valid_care_sites)
    _logger.info("7. Closing linked accesses")
    AccessesService.close_accesses(perimeters_to_delete)
    _logger.info("End of perimeters updating. Invalidating cache for Perimeters and Accesses")
    invalidate_cache(model_name=Perimeter.__name__)
    invalidate_cache(model_name=Access.__name__)
