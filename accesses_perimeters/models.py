import logging

from django.conf import settings
from django.db import models

from accesses_perimeters.apps import AccessesPerimetersConfig

APP_LABEL = AccessesPerimetersConfig.name
DB_ALIAS = AccessesPerimetersConfig.DB_ALIAS

_logger = logging.getLogger("django.request")


class ModelManager(models.Manager):
    def get_queryset(self):
        if DB_ALIAS not in settings.DATABASES:
            _logger.error(f"`{DB_ALIAS}` is missing from settings.DATABASES")
            return
        q = super().get_queryset()
        q._db = DB_ALIAS
        return q


class ConceptFhir(models.Model):
    source_concept_id = models.IntegerField(primary_key=True)
    source_concept_name = models.TextField(blank=True, null=True)
    objects = ModelManager()

    class Meta:
        app_label = APP_LABEL
        managed = False
        db_table = "concept_fhir"


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
    objects = ModelManager()

    class Meta:
        app_label = APP_LABEL
        managed = False
        db_table = "care_site"

    @staticmethod
    def sql_get_deleted_care_sites() -> str:
        return """SELECT DISTINCT care_site_id, delete_datetime
                  FROM omop.care_site
                  WHERE delete_datetime IS NOT NULL
               """


class ListCohort(models.Model):
    row_id = models.BigIntegerField(primary_key=True)
    hash = models.BigIntegerField(null=True)
    insert_datetime = models.DateTimeField(null=True)
    update_datetime = models.DateTimeField(null=True)
    delete_datetime = models.DateTimeField(null=True)
    change_datetime = models.DateTimeField(null=True)
    id = models.BigIntegerField(null=True)
    status = models.TextField(blank=True, null=True)
    _sourcereferenceid = models.BigIntegerField(null=True)
    source_reference = models.TextField(blank=True, null=True, db_column="source__reference")
    source_type = models.TextField(blank=True, null=True, db_column="source__type")
    mode = models.TextField(blank=True, null=True)
    title = models.TextField(blank=True, null=True)
    subject_type = models.TextField(blank=True, null=True, db_column="subject__type")
    date = models.DateTimeField(null=True)
    note_query_text = models.TextField(blank=True, null=True, db_column="note___query__text")
    objects = ModelManager()

    class Meta:
        app_label = APP_LABEL
        managed = False
        db_table = "list"

    @classmethod
    def get_practitioner_patient_lists_since(cls, since_dt: str):
        sql = f"""
                  SELECT *
                  FROM omop.list
                  WHERE source__type = 'Practitioner'
                    AND subject__type = 'Patient'
                    AND insert_datetime >= '{since_dt}';
                  """
        return ListCohort.objects.raw(sql)


class CareSiteMapperMep(models.Model):
    # Colonnes de la table
    old_prod_b_id = models.BigIntegerField(db_column="old_prod_b_id", primary_key=True)
    new_prod_a_id = models.BigIntegerField(db_column="new_prod_a_id")
    care_site_id = models.BigIntegerField(db_column="care_site_id")
    objects = ModelManager()

    class Meta:
        app_label = APP_LABEL
        managed = False
        db_table = "caresite_mapper_mep"

    def __str__(self) -> str:
        return f"{self.old_prod_b_id} -> {self.new_prod_a_id} (care_site_id={self.care_site_id})"
