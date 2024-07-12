from __future__ import annotations

import os
from typing import List

from django.conf import settings
from django.db import models


env = os.environ

DOMAIN_CONCEPT_ID = env.get("DOMAIN_CONCEPT_COHORT")  # 1147323
RELATIONSHIP_CONCEPT_ID = env.get("FACT_RELATIONSHIP_CONCEPT_COHORT")  # 44818821


class OmopModelManager(models.Manager):
    def get_queryset(self):
        q = super(OmopModelManager, self).get_queryset()
        q._db = settings.OMOP_DB_ALIAS
        return q


class Concept(models.Model):
    concept_id = models.IntegerField(primary_key=True)
    concept_name = models.TextField(blank=True, null=True)
    objects = OmopModelManager()

    class Meta:
        managed = False
        db_table = 'concept'


class FactRelationship(models.Model):
    row_id = models.BigIntegerField(primary_key=True)
    fact_id_1 = models.BigIntegerField()
    fact_id_2 = models.BigIntegerField()
    objects = OmopModelManager()

    class Meta:
        managed = False
        db_table = 'fact_relationship'

    @staticmethod
    def sql_get_cohort_source_populations(cohorts_ids: List[str]) -> str:
        return f"""
        SELECT row_id, fact_id_1, fact_id_2
        FROM omop.fact_relationship
        WHERE delete_datetime IS NULL
        AND domain_concept_id_1 = {DOMAIN_CONCEPT_ID}
        AND domain_concept_id_2 = {DOMAIN_CONCEPT_ID}
        AND relationship_concept_id = {RELATIONSHIP_CONCEPT_ID}
        AND fact_id_1 IN ({",".join(cohorts_ids)})
        """


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
