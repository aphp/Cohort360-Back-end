import logging

from django.conf import settings
from django.db import models

from accesses_perimeters.apps import AccessesPerimetersConfig

APP_LABEL = AccessesPerimetersConfig.name
DB_ALIAS = AccessesPerimetersConfig.DB_ALIAS

logger = logging.getLogger(__name__)


class ModelManager(models.Manager):

    def get_queryset(self):
        if DB_ALIAS not in settings.DATABASES:
            logger.error(f"`{DB_ALIAS}` is missing from settings.DATABASES")
            return
        q = super().get_queryset()
        q._db = DB_ALIAS
        return q


class Concept(models.Model):
    concept_id = models.IntegerField(primary_key=True)
    concept_name = models.TextField(blank=True, null=True)
    objects = ModelManager()

    class Meta:
        app_label = APP_LABEL
        managed = False
        db_table = 'concept'


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
        db_table = 'care_site'

    @staticmethod
    def sql_get_deleted_care_sites() -> str:
        return """SELECT DISTINCT care_site_id, delete_datetime 
                  FROM omop.care_site WHERE delete_datetime IS NOT NULL
               """
