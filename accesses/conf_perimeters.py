from __future__ import annotations

import os

from typing import List, Union, OrderedDict, Dict

from django.db import models
from django.db.models import Q, Max
from django.utils import timezone
from rest_framework import serializers

from accesses.models import Perimeter
from admin_cohort import settings, app
from admin_cohort.tools import prettify_dict

env = os.environ

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

MAIN_CARE_SITE_ID = 8312002244


# OMOP PROVIDER ################################################################

class OmopModelManager(models.Manager):
    def get_queryset(self):
        q = super(OmopModelManager, self).get_queryset()
        q._db = "omop"
        return q


class Provider(models.Model):
    provider_id = models.IntegerField(primary_key=True)
    provider_source_value = models.TextField()
    valid_start_datetime = models.DateTimeField()
    valid_end_datetime = models.DateTimeField()

    objects = OmopModelManager()

    class Meta:
        managed = False
        db_table = 'provider'


def get_provider_id(user_id: str) -> int:
    p: Provider = Provider.objects.filter(
        Q(provider_source_value=user_id)
        & (Q(valid_start_datetime__lte=timezone.now())
           | Q(valid_start_datetime__isnull=True))
        & (Q(valid_end_datetime__gte=timezone.now())
           | Q(valid_end_datetime__isnull=True))).first()
    if p is None:
        from accesses.models import Profile
        return Profile.objects.aggregate(
            Max("provider_id"))['provider_id__max'] + 1
    return p.provider_id


# TASKS ########################################################################


class Concept(models.Model):
    concept_id = models.IntegerField(primary_key=True)
    concept_name = models.TextField(blank=True, null=True)

    objects = OmopModelManager()

    class Meta:
        managed = False
        db_table = 'concept'


class CareSite(models.Model):
    care_site_id = models.BigIntegerField(primary_key=True)
    care_site_source_value = models.TextField(blank=True, null=True)
    care_site_name = models.TextField(blank=True, null=True)
    care_site_short_name = models.TextField(blank=True, null=True)
    care_site_type_source_value = models.TextField(blank=True, null=True)

    objects = OmopModelManager()

    class Meta:
        managed = False
        db_table = 'care_site'


def where_conditions(
        fact_rel_name: str, cs_names: Union[str, List[str]],
        cs_domain_concept_id: int, is_part_of_rel_id: int
) -> str:
    cs_names = [cs_names] if not isinstance(cs_names, list) else cs_names

    cs_conditions = ' AND '.join([
        f"""
            {cs_name}.care_site_type_source_value IN ({
        ','.join([
            f"'{id}'" for id in settings.PERIMETERS_TYPES
        ])
        })
        """ for cs_name in cs_names
    ])

    return f"""
        {fact_rel_name}.domain_concept_id_1={cs_domain_concept_id}
        AND {fact_rel_name}.domain_concept_id_2={cs_domain_concept_id}
        AND {fact_rel_name}.relationship_concept_id={is_part_of_rel_id}
        AND {cs_conditions}
    """


def sql_care_site_children(care_site_ids: List[int], cs_domain_concept_id: int,
                           is_part_of_rel_id: int) -> str:
    ids = ','.join([f"'{id}'" for id in care_site_ids])
    return f"""
        WITH RECURSIVE child as (
            SELECT
                cs.*, CAST(fr.fact_id_2 AS BIGINT) parent_id
            FROM
                omop.care_site cs
            JOIN
                omop.fact_relationship fr
            ON
                cs.care_site_id=fr.fact_id_1
            WHERE (
                cs.care_site_id IN ({ids})
                AND {where_conditions('fr', 'cs',
                                      cs_domain_concept_id, is_part_of_rel_id)}
            )
            UNION
                SELECT
                    css.*, CAST(frr.fact_id_2 AS BIGINT) parent_id
                FROM omop.care_site css
                JOIN
                    omop.fact_relationship frr
                ON
                    css.care_site_id=frr.fact_id_1
                INNER JOIN
                    child c
                ON
                    c.care_site_id=frr.fact_id_2
                WHERE ({where_conditions('frr', 'css', cs_domain_concept_id,
                                         is_part_of_rel_id)})
        ) SELECT * FROM child
    """


# In this Serializer, we expect input data to already furnish a parent_id value
class CareSiteSerializerFaster(serializers.ModelSerializer):
    parent_id = serializers.IntegerField(allow_null=True)

    id = serializers.IntegerField(source='care_site_id')
    type_source_value = serializers.CharField(
        source='care_site_type_source_value')

    class Meta:
        model = CareSite
        fields = [
            "id",
            "type_source_value",
            "care_site_id",
            "care_site_name",
            "care_site_short_name",
            "care_site_type_source_value",
            "care_site_source_value",
            "parent_id",
        ]
        read_only_fields = [
            "care_site_id",
            "care_site_name",
            "care_site_short_name",
            "care_site_type_source_value",
            "care_site_source_value",
            "parent_id",
        ]


def treefy_perimeters(
        css: List[OrderedDict], ids_to_filter: Union[List[str], None] = None
) -> List[OrderedDict]:
    def complete_parents(full_dct: Dict[int, OrderedDict], focus_dct,
                         use_filter: bool = False,
                         end_result: Dict[str, OrderedDict] = {}):
        """
        Given the overall dictionary of care-sites full_dct,
        For each care-site that is required to be attached to their parent
         in focus_dct
        If the id is in the ids_to_filter, in the case use_filter=True

        If the parent_id is null or if the care-site is the main AP-HP one, then
            the care-site will figure in the end_result

        else, if the parent figures in full_dct
        The parent will see its 'children' completed by the current care-site
            if it is not already there
        If there is ids_to_filter, then the parent will be added to next_step
            so that next iteration will look for its parent
        We finally iterate on this function if next_step is not empty, keeping
            in memory end_result already found
        @param full_dct: dict containing all the care-sites
        @param focus_dct: dict containing the care-sites we want to include
        in their parents' children field
        @param use_filter: say if we filter the focus_dict's caresites
            by ids_to_filter (should be True only for first call)
        @param end_result: contains the parentless caresites we already know
        @return: list of Perimeters that are completed with children field
        """
        next_step = {}
        parent_completed = {}

        for cs in focus_dct.values():
            p_id = cs.get('parent_id', None)
            cs_id = cs['id']
            if not use_filter or ids_to_filter is None \
                    or cs_id in ids_to_filter:
                if (not p_id
                        or p_id not in full_dct
                        or cs["type_source_value"] ==
                        settings.ROOT_PERIMETER_TYPE):
                    end_result.setdefault(cs_id, cs)

                elif p_id in full_dct:
                    parent = full_dct[p_id]
                    p_chld = parent.setdefault("children", [])
                    if cs not in p_chld:
                        parent["children"] = p_chld + [cs]
                        parent_completed.setdefault(cs_id)

                    # if there is no filter in the beginning, it means
                    # all care-sites are kept, thus no next-step
                    if ids_to_filter is not None and len(ids_to_filter):
                        next_step.setdefault(p_id, parent)

        # perimeter that have already been into the process of completing
        # the matching parent are removed from next step
        [next_step.pop(k, None) for k in list(next_step.keys()) if
         k in parent_completed]

        if len(next_step):
            return complete_parents(full_dct, next_step, False, end_result)
        return list(end_result.values())

    dct = dict([(cs["id"], cs) for cs in css])

    return complete_parents(dct, dct, True)


IS_PART_OF_RELATONSHIP_NAME = "Care Site is part of Care Site"
CONTAINS_RELATIONSHIP_NAME = "Care Site contains Care Site"
CARE_SITE_DOMAIN_CONCEPT_NAME = "Care site"

perim_fields_to_care_site = dict(
    source_value="care_site_source_value",
    name="care_site_name",
    short_name="care_site_short_name",
    type_source_value="care_site_type_source_value",
)


def fill_up_care_sites():
    print("Building query for care-sites")
    try:
        is_part_of_rel_id = Concept.objects.get(
            concept_name=IS_PART_OF_RELATONSHIP_NAME
        ).concept_id
        cs_domain_concept_id = Concept.objects.get(
            concept_name=CARE_SITE_DOMAIN_CONCEPT_NAME
        ).concept_id
    except Exception as e:
        raise Exception(f"Error while getting Concepts: {e}")

    q = CareSite.objects.raw(sql_care_site_children(
        [MAIN_CARE_SITE_ID], cs_domain_concept_id, is_part_of_rel_id))

    print("Building care-site tree")
    tree = treefy_perimeters(list(CareSiteSerializerFaster(q, many=True).data))

    for c in tree:
        c['parent_id'] = None

    children = tree
    to_delete = []
    all_changes = dict()
    while children:
        level = children[0]['care_site_type_source_value']
        print(f"Inserting/updating {len(children)} perimeters, "
              f"level : {level}")
        all_changes[level] = dict(new=dict(), deleted=dict(), updated=dict())

        dct_children = dict([(c['care_site_id'], c) for c in children])
        existing: List[Perimeter] = Perimeter.objects.filter(
            local_id__in=dct_children.keys()).prefetch_related('parent')

        to_update = []
        to_create: List[Perimeter] = []
        for p in existing:
            try:
                omop_id = int(p.local_id)
                if omop_id in dct_children:
                    c = dct_children[omop_id]
                    changes = {}

                    new_parent: Perimeter = None

                    for p_f, cs_f in perim_fields_to_care_site.items():
                        if getattr(p, p_f) != c.get(cs_f):
                            changes[p_f] = getattr(p, p_f)
                            setattr(p, p_f, c.get(cs_f))

                    if str(p.parent and p.parent.local_id) != str(c.get('parent_id')):
                        changes['parent_id'] = p.parent_id
                        new_parent = Perimeter.objects.get(
                            local_id=str(c.get('parent_id')))
                        p.parent_id = new_parent.id

                    if len(changes):
                        all_changes[level]['updated'][p.local_id] = dict([
                          (ch, f"{old_value} -> {getattr(p, ch)}"
                              if ch != 'parent_id'
                              else f"{p.parent.name}({p.parent.local_id}) -> {new_parent and new_parent.name}({c.get('parent_id')})")
                          for (ch, old_value) in changes.items()])
                        to_update.append(p)
                    dct_children.pop(omop_id)
                else:
                    all_changes[level]['deleted'][p.local_id] = p.name
                    to_delete.append(p)
            except Exception:
                pass

        for cs in dct_children.values():
            p = Perimeter(
                local_id=str(cs['care_site_id']),
                source_value=c['care_site_source_value'],
                name=c['care_site_name'],
                short_name=c['care_site_short_name'],
                type_source_value=c['care_site_type_source_value'],
                parent_id=c['parent_id']
            )
            all_changes[level]['new'][str(cs['care_site_id'])] = p.__dict__
            to_create.append(p)

        if len(to_create):
            Perimeter.objects.bulk_create(to_create)
        if len(to_update):
            Perimeter.objects.bulk_update(to_update, [
                "source_value", "name", "short_name", "type_source_value",
                "parent_id"])
        children = sum([c.get('children', []) for c in children], [])

        for k in ['new', 'deleted', 'updated']:
            if len(all_changes[level][k]) == 0:
                all_changes[level].pop(k)
        if len(all_changes[level]) == 0:
            all_changes.pop(level)

    for to_del in to_delete:
        to_del.delete()
    print(f"Changes : {prettify_dict(all_changes)}")
    print("Perimeters updated")


@app.task()
def care_sites_daily_update():
    # runs between 2am and 3am
    if timezone.now().hour != 2:
        return
    fill_up_care_sites()
