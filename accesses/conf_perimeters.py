from __future__ import annotations

import os
from typing import List

from django.db import models
from django.db.models import Q, Max
from django.utils import timezone

from accesses.models import Perimeter, Access
from admin_cohort import settings, app

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

# SETTINGS CONFIGURATION ###############################################################################################
env = os.environ
# Configuration of OMOP connexion
settings.DATABASES.__setitem__(
    'omop', {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': env.get("DB_OMOP_NAME"),
        'USER': env.get("DB_OMOP_USER"),
        'PASSWORD': env.get("DB_OMOP_PASSWORD"),
        'HOST': env.get("DB_OMOP_HOST"),
        'PORT': env.get("DB_OMOP_PORT"),
        'DISABLE_SERVER_SIDE_CURSORS': True,
        'OPTIONS': {
            'options': f"-c search_path={env.get('DB_OMOP_SCHEMA')},public"
        },
    }, )

# CLASS DEFINITION ####################################################################################################
"""
Model Manager init
It used to simplify sql SELECT query and Model Mapping

for example in Concept => Concept.object.get(concept_name='My name') is equivalent to
Concept.object.raw("SELECT * FROM omop.concept WHERE concept_name='My name';")
"""


class OmopModelManager(models.Manager):
    def get_queryset(self):
        q = super(OmopModelManager, self).get_queryset()
        q._db = "omop"
        return q


class Concept(models.Model):
    concept_id = models.IntegerField(primary_key=True)
    concept_name = models.TextField(blank=True, null=True)
    objects = OmopModelManager()

    class Meta:
        managed = False
        db_table = 'concept'


""""
Model Provider (= User informations)
"""


class Provider(models.Model):
    provider_id = models.IntegerField(primary_key=True)
    provider_source_value = models.TextField()
    valid_start_datetime = models.DateTimeField()
    valid_end_datetime = models.DateTimeField()
    objects = OmopModelManager()

    class Meta:
        managed = False
        db_table = 'provider'


class CareSite(models.Model):
    care_site_id = models.BigIntegerField(primary_key=True)
    care_site_source_value = models.TextField(blank=True, null=True)
    care_site_name = models.TextField(blank=True, null=True)
    care_site_short_name = models.TextField(blank=True, null=True)
    care_site_type_source_value = models.TextField(blank=True, null=True)
    care_site_parent_id = models.BigIntegerField(null=True)
    cohort_id = models.BigIntegerField(null=True)
    cohort_size = models.BigIntegerField(null=True)
    delete_datetime = models.DateTimeField(null=True)
    objects = OmopModelManager()

    class Meta:
        managed = False
        db_table = 'care_site'


class RelationPerimeter:
    def __init__(self, above_levels_ids: str, children: str, full_path: str):
        self.above_levels_ids = above_levels_ids
        self.children = children
        self.full_path = full_path


# FUNCTION DEFINITION #################################################################################################

# TODO: check si doit changer avec l'issue de modification du profile id par le provider_source_value (code aph du user)
# TODO: qu'est ce que ça fiche ici, à déplacer dans le script appelé
def get_provider_id(user_id: str) -> int:
    """"
    For one user id return the provider id associate
    """
    p: Provider = Provider.objects.filter(Q(provider_source_value=user_id)
                                          & (Q(valid_start_datetime__lte=timezone.now())
                                             | Q(valid_start_datetime__isnull=True))
                                          & (Q(valid_end_datetime__gte=timezone.now())
                                             | Q(valid_end_datetime__isnull=True))).first()
    if p is None:
        from accesses.models import Profile
        return Profile.objects.aggregate(Max("provider_id"))['provider_id__max'] + 1
    return p.provider_id


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
    except Exception as e:
        raise Exception(f"Error while getting Concepts: {e}")
    return str(is_part_of_rel_id), str(cs_domain_concept_id)


def cast_to_list_ids(item) -> List[int]:
    """
    Simple function to be type tolerant of env value fetch for top hierarchy care_site ids
    """
    if isinstance(item, (tuple, list)):
        return list(item)
    elif isinstance(item, str):
        try:
            return [int(i) for i in item.replace(" ", "").split(",")]
        except Exception as err:
            raise Exception(f"Error while try to cast {item} to integer list: {err}")
    else:
        return [item]


def get_top_hierarchy_care_site_ids() -> List[int]:
    """
    return list of top hierarchy care sites
    """
    try:
        list_top_care_site_ids = env.get("TOP_HIERARCHY_CARE_SITE_IDS")
    except Exception as e:
        raise Exception(f"Error while getting Top hierarchy care_site_ids (var:TOP_HIERARCHY_CARE_SITE_IDS): {e}")
    return cast_to_list_ids(list_top_care_site_ids)


"""
PSQL query to get all filtred care sites with the direct parent associate.
it will use 2 tables from OMOP PG:  omop.care_site and omop.fact_relationship
"""


def psql_query_care_site_relationship(top_care_site_ids: list) -> str:
    is_part_of_rel_id, cs_domain_concept_id = get_concept_filter_id()
    return f"""
            WITH care_sites AS (
            SELECT cs.care_site_id,
            cs.care_site_name,
            cs.care_site_short_name,
            cs.care_site_type_source_value,
            cs.care_site_source_value,
            NULL as care_site_parent_id,
            cd.cohort_definition_id as cohort_id,
            cd.cohort_size as cohort_size
            FROM omop.care_site cs
            INNER JOIN omop.cohort_definition cd
            ON cd.owner_entity_id = cs.care_site_id
            WHERE (cs.care_site_id IN ({str(top_care_site_ids)[1:-1]})
            AND cs.delete_datetime IS NULL
            AND cd.delete_datetime IS NULL AND cd.owner_domain_id = 'Care_site'
            )
            UNION
            SELECT
            css.care_site_id,
            css.care_site_name,
            css.care_site_short_name,
            css.care_site_type_source_value,
            css.care_site_source_value,
            CAST(frr.fact_id_2 AS BIGINT) care_site_parent_id,
            cd.cohort_definition_id as cohort_id,
            cd.cohort_size as cohort_size
            FROM omop.care_site css
            INNER JOIN omop.fact_relationship frr
            ON css.care_site_id=frr.fact_id_1
            INNER JOIN omop.cohort_definition cd
            ON cd.owner_entity_id = css.care_site_id
            WHERE (
            frr.fact_id_1!=frr.fact_id_2
            AND frr.domain_concept_id_1={cs_domain_concept_id}
            AND frr.domain_concept_id_2={cs_domain_concept_id}
            AND frr.relationship_concept_id={is_part_of_rel_id}
            AND css.care_site_type_source_value IN ({str(settings.PERIMETERS_TYPES)[1:-1]})
            AND css.delete_datetime IS NULL
            AND frr.delete_datetime IS NULL
            AND cd.delete_datetime IS NULL AND cd.owner_domain_id = 'Care_site'
            ))
             SELECT DISTINCT * FROM care_sites ;"""


"""
Mapping between care_site object to Perimeter Model
"""


def map_to_perimeter(care_site_object: CareSite, relation_perimeter: RelationPerimeter):
    return Perimeter(
        id=care_site_object.care_site_id,
        local_id=str(care_site_object.care_site_id),
        source_value=care_site_object.care_site_source_value,
        name=care_site_object.care_site_name,
        short_name=care_site_object.care_site_short_name,
        type_source_value=care_site_object.care_site_type_source_value,
        parent_id=care_site_object.care_site_parent_id,
        above_levels_ids=relation_perimeter.above_levels_ids,
        inferior_levels_ids=relation_perimeter.children,
        full_path=relation_perimeter.full_path,
        cohort_id=care_site_object.cohort_id,
        cohort_size=care_site_object.cohort_size
    )


def log_insert_update(care_site_levels, new_previous_level_list, list_perimeter_to_create,
                      list_perimeter_to_update):
    print(f"Process at levels: {set(care_site_levels)}"
          f"\n- Perimeters already existing: {len(new_previous_level_list)}"
          f"\n- Perimeters to Create: {len(list_perimeter_to_create)} "
          f"\n- Perimeters to update: {len(list_perimeter_to_update)} ")


def get_path(perimeter: Perimeter, care_site: CareSite) -> str:
    return f"{perimeter.full_path}/{care_site.care_site_source_value}-{care_site.care_site_name}"


def is_care_site_different_from_perimeter(care_site: CareSite, perimeter: Perimeter,
                                          relation_perimeter: RelationPerimeter):
    if care_site.care_site_parent_id != perimeter.parent_id or \
            care_site.care_site_type_source_value != perimeter.type_source_value or \
            care_site.care_site_name != perimeter.name or \
            care_site.care_site_short_name != perimeter.short_name or \
            care_site.delete_datetime != perimeter.delete_datetime or \
            care_site.cohort_id != int(perimeter.cohort_id) or \
            care_site.cohort_size != int(perimeter.cohort_size) or \
            relation_perimeter.above_levels_ids != perimeter.above_levels_ids or \
            relation_perimeter.full_path != perimeter.full_path or \
            relation_perimeter.children != perimeter.inferior_levels_ids:
        return True
    return False


"""
Check with perimeters objects already existing if we have to insert a new perimeter or just update it:
it append in 2 respective list perimeters object.
"""


def insert_update_perimeter_list_append(insert_list: [Perimeter], update_list: [Perimeter],
                                        existing_perimeters: [Perimeter], care_site: CareSite,
                                        relation_perimeter: RelationPerimeter,
                                        new_previous_level_perimeter: [Perimeter]):
    check_perimeter = [perimeter for perimeter in existing_perimeters if care_site.care_site_id == perimeter.id]
    if len(check_perimeter) > 0:
        compare_perimeter = check_perimeter[0]
        if is_care_site_different_from_perimeter(care_site, compare_perimeter, relation_perimeter):
            update_list.append(map_to_perimeter(care_site, relation_perimeter))
        else:
            new_previous_level_perimeter.append(compare_perimeter)

    else:
        insert_list.append(map_to_perimeter(care_site, relation_perimeter))


def get_parent_perimeter_in_perimeter_list(perimeter_list: [Perimeter], parent_id: int) -> Perimeter:
    parent: [Perimeter] = [perimeter for perimeter in perimeter_list if
                           perimeter.id == parent_id]
    if len(parent) == 0:
        raise f"ERROR: {parent_id} has no previous perimeters wiht the same id"
    return parent[0]


"""
Return well formatted above list
"""


def get_above_from_parent_perimeter(care_site: CareSite, parent_perimeter: Perimeter) -> str:
    return parent_perimeter.above_levels_ids + f"{care_site.care_site_parent_id},"


"""
Method to create perimeters at the top of hierarchy
"""


def create_current_perimeter_level(care_site_id_list: List[int], care_site_objects: [CareSite],
                                   existing_perimeters: [Perimeter]) -> [Perimeter]:
    # init var
    if existing_perimeters is None:
        existing_perimeters = list()

    list_perimeter_to_create = []
    list_perimeter_to_update = []
    care_site_levels = []
    current_perimeters = []
    # for every care_site where id is in current id list we map to perimeter and add it to a list
    for care_site in care_site_objects:
        if care_site.care_site_id in care_site_id_list:
            # get root path
            path = f"{care_site.care_site_source_value}-{care_site.care_site_name}"
            print(path)
            # get all ids from below levels
            children = get_children_care_site_list_by_id(care_site_objects, care_site.care_site_id)
            # Generate RelationPerimeter Object to simplify function param use:
            relation_perimeters = RelationPerimeter(above_levels_ids="", children=children, full_path=path)
            print(relation_perimeters.full_path)
            insert_update_perimeter_list_append(list_perimeter_to_create, list_perimeter_to_update,
                                                existing_perimeters, care_site, relation_perimeters,
                                                current_perimeters)
            care_site_levels.append(care_site.care_site_type_source_value)
    log_insert_update(care_site_levels, current_perimeters, list_perimeter_to_create, list_perimeter_to_update)

    # INSERT/UPDATE PERIMETERS
    insert_perimeter(list_perimeter_to_create)
    update_perimeter(list_perimeter_to_update)
    return current_perimeters + list_perimeter_to_create + list_perimeter_to_update


"""
Recursive function to create by bulk_create method all perimeters from care_site list in the hierarchy order
Is starts from the top to the leafs
"""


def sequential_recursive_create_children_perimeters(care_site_id_list: list, care_site_objects: [CareSite],
                                                    existing_perimeters: list,
                                                    previous_level_perimeters: [Perimeter]):
    # init var
    if existing_perimeters is None:
        existing_perimeters = list()

    care_site_objects_copy = list(care_site_objects)
    children_care_site_objects = []
    list_perimeter_to_create = []
    list_perimeter_to_update = []
    list_current_parent_id = []
    care_site_levels = []
    new_previous_level_list = []
    # for every care_site where id is in current parent id list we map to perimeter and add it to a list
    for care_site in care_site_objects_copy:
        if care_site.care_site_parent_id in care_site_id_list:
            if care_site.care_site_id in list_current_parent_id:
                print(f"warn: Care site {care_site.care_site_id} has 2 or more parents !")
                continue

            # We get the previous above_levels_ids value from parent perimeter and add current id
            parent_perimeter = get_parent_perimeter_in_perimeter_list(previous_level_perimeters,
                                                                      care_site.care_site_parent_id)

            relation_perimeter = RelationPerimeter(
                above_levels_ids=get_above_from_parent_perimeter(care_site, parent_perimeter),
                children=get_children_care_site_list_by_id(care_site_objects, care_site.care_site_id),
                full_path=get_path(parent_perimeter, care_site))

            insert_update_perimeter_list_append(list_perimeter_to_create, list_perimeter_to_update,
                                                existing_perimeters, care_site, relation_perimeter,
                                                new_previous_level_list)

            list_current_parent_id.append(care_site.care_site_id)
            care_site_levels.append(care_site.care_site_type_source_value)
        else:
            children_care_site_objects.append(care_site)

    print(f"Children care_site objects found: {len(children_care_site_objects)}")

    if len(list_perimeter_to_create) > 0 or len(list_perimeter_to_update) > 0 or len(new_previous_level_list) > 0:
        log_insert_update(care_site_levels, new_previous_level_list, list_perimeter_to_create,
                          list_perimeter_to_update)
        insert_perimeter(list_perimeter_to_create)
        update_perimeter(list_perimeter_to_update)
        # we save all current level perimeters to the next previous perimeters list
        new_previous_level_list = new_previous_level_list + list_perimeter_to_create + list_perimeter_to_update
        # run function with new current parent id list and children objects to go to lower care_site level
        sequential_recursive_create_children_perimeters(list_current_parent_id, children_care_site_objects,
                                                        existing_perimeters, new_previous_level_list)
    # If there is no more perimeter to add, end of recursive function


"""
Delete all objects of Perimeter data Model
"""


def clean_all_perimeters():
    perimeters_all = Perimeter.objects.all()
    print(f"{len(perimeters_all)} Perimeters objects found in data model; Start to delete all perimeters:")
    try:
        perimeters_all.delete()
    except Exception as error:
        raise Exception(f"Error while trying to remove all perimeters: {error}")


"""
Bulk update data Perimeters
"""


def update_perimeter(list_perimeter_to_update: List[Perimeter]):
    if len(list_perimeter_to_update) == 0:
        return
    Perimeter.objects.bulk_update(list_perimeter_to_update,
                                  ["source_value", "name", "short_name", "type_source_value", "parent_id",
                                   "above_levels_ids", "full_path", "inferior_levels_ids", "delete_datetime",
                                   "cohort_id", "cohort_size"])


"""
Bulk update data Access
"""


def update_accesses(list_access_to_update: List[Perimeter]):
    if len(list_access_to_update) > 0:
        Access.objects.bulk_update(list_access_to_update, ["manual_end_datetime"])


"""
Bulk create data Perimeters
"""


def insert_perimeter(list_perimeter_to_create: List[Perimeter]):
    if len(list_perimeter_to_create) == 0:
        return
    Perimeter.objects.bulk_create(list_perimeter_to_create)


"""
Return simple mapping of care_site and delete_datetime in dictionary
"""


def get_dict_deleted_care_site() -> dict:
    all_deleted_care_site = CareSite.objects.raw("SELECT DISTINCT care_site_id, delete_datetime "
                                                 "FROM omop.care_site "
                                                 "WHERE delete_datetime IS NOT NULL")
    care_site_deleted_dict = dict()
    for care_site in all_deleted_care_site:
        care_site_deleted_dict[care_site.care_site_id] = care_site.delete_datetime
    return care_site_deleted_dict


"""
Update perimeters with the correct delete_datetime:
- 2 checks: if perimeter is associated with deleted care_site
            if perimeter get reference not in valid care_site hierarchy
"""


def delete_perimeters_and_accesses(existing_perimeters: List[Perimeter], all_valid_care_site: List[CareSite]):
    deleted_perimeters = get_all_perimeters_with_no_valid_care_site(existing_perimeters,
                                                                    get_dict_deleted_care_site(),
                                                                    all_valid_care_site)
    if len(deleted_perimeters) > 0:
        print(f"WARN: {len(deleted_perimeters)} perimeters to deleted")
        update_perimeter(deleted_perimeters)
        print("Start to close Accesses linked to removed Perimeters or with no perimeters")
        close_access(deleted_perimeters)

    else:
        print("No perimeters deleted")


"""
get boolean filter if manual or end date is not superior
"""


def filter_end_date(access: Access) -> bool:
    return (access.manual_end_datetime is None or access.manual_end_datetime > timezone.now()) and \
           (access.end_datetime is None or access.end_datetime > timezone.now())


"""
Check if all valid accesses are linked to deleted perimeter or no perimeter are assigned
It add a date to manual end datetiem field with current datetime to close each accesses found.
"""


def close_access(deleted_perimeter_ids: List[Perimeter]):
    # get only valid accesses
    all_access = [access for access in Access.objects.all() if filter_end_date(access)]
    ids_perimeter_list = [perimeter.id for perimeter in deleted_perimeter_ids]
    deleted_access_list = []
    print("List Accesses to update:")
    for access in all_access:
        if access.perimeter_id in ids_perimeter_list or access.perimeter_id is None:
            access.manual_end_datetime = timezone.now()
            deleted_access_list.append(access)
            print(f"Access {access.id}")
    if len(deleted_access_list) > 0:
        print(f" {len(deleted_access_list)} Accesses to update.")
        update_accesses(deleted_access_list)
    else:
        print("No accesses to update")


"""
Get list of perimeters deleted with the correct delete_datetime
"""


def get_all_perimeters_with_no_valid_care_site(existing_perimeters: List[Perimeter], deleted_care_site: dict,
                                               all_valid_care_site: List[CareSite]):
    all_removed_perimeters = []
    care_site_ids_list = [care_site.care_site_id for care_site in all_valid_care_site]
    for perimeter in existing_perimeters:
        if perimeter.id in deleted_care_site.keys():
            care_site_delete_datetime = deleted_care_site[perimeter.id]
            print(f"Perimeter {perimeter.id} reference to deleted care_site at {care_site_delete_datetime}")
            perimeter.delete_datetime = care_site_delete_datetime
            print(f"new delete date: {perimeter.delete_datetime}")
            all_removed_perimeters.append(perimeter)
        elif perimeter.id not in care_site_ids_list:
            print(f"Perimeter {perimeter.id} is not in care_site hierarchy anymore")
            perimeter.delete_datetime = timezone.now()
            all_removed_perimeters.append(perimeter)
    return all_removed_perimeters


"""
return a String list of all direct children care sites
"""


def get_children_care_site_list_by_id(all_care_site: [CareSite], current_care_site_id: int) -> str:
    return str([care_site.care_site_id for care_site in all_care_site if
                care_site.care_site_parent_id == current_care_site_id])[1:-1]


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
    print("Get top hierarchy ids")
    top_care_site_ids = get_top_hierarchy_care_site_ids()

    print("Building query for care-sites")
    all_valid_care_site_relationship = CareSite.objects.raw(psql_query_care_site_relationship(top_care_site_ids))

    print(f"Fetch {len(all_valid_care_site_relationship)} care sites from OMOP DB")
    # ! "even_deleted=True" to take also delete_datetime non null
    existing_perimeters = Perimeter.objects.all(even_deleted=True)

    print("Start Top hierarchy Perimeter objects creation")
    top_perimeters_list = create_current_perimeter_level(top_care_site_ids, all_valid_care_site_relationship,
                                                         existing_perimeters)
    print("Start recursive Perimeter objects creation")
    sequential_recursive_create_children_perimeters(top_care_site_ids, all_valid_care_site_relationship,
                                                    existing_perimeters, top_perimeters_list)
    print("Start deletion of removed perimeters")
    delete_perimeters_and_accesses(existing_perimeters, all_valid_care_site_relationship)
    print("End of perimeters updating")


# TODO : le Cron lance la fonction toutes les heures d'où la vérification du timezone now... solution sale à remplacer!


@app.task()
def care_sites_daily_update():
    # runs between 2am and 3am
    if timezone.now().hour != 2:
        return
    perimeters_data_model_objects_update()
