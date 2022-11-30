from coverage.annotate import os
from django.db import models
from django.db.models import QuerySet

from accesses.conf_perimeters import OmopModelManager
from accesses.models import Perimeter, Access, Role
from accesses.tools.perimeter_process import get_perimeters_ids_list
from admin_cohort import settings

ROLE = "role"
READ_PATIENT_NOMI = "read_patient_nomi"
READ_PATIENT_PSEUDO = "read_patient_pseudo"
EXPORT_CSV_NOMI = "export_csv_nomi"
EXPORT_CSV_PSEUDO = "export_csv_pseudo"
EXPORT_JUPYTER_NOMI = "export_jupyter_nomi"
EXPORT_JUPYTER_PSEUDO = "export_jupyter_pseudo"
SEARCH_IPP = "search_ipp"

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


def get_dict_right_accesses(user_accesses: [Access]) -> dict:
    return {READ_PATIENT_NOMI: user_accesses.filter(Role.is_read_patient_role_nominative(ROLE)),
            READ_PATIENT_PSEUDO: user_accesses.filter(Role.is_read_patient_role(ROLE)),
            EXPORT_CSV_NOMI: user_accesses.filter(Role.is_export_csv_nominative_role(ROLE)),
            EXPORT_CSV_PSEUDO: user_accesses.filter(Role.is_export_csv_pseudo_role(ROLE)),
            EXPORT_JUPYTER_NOMI: user_accesses.filter(Role.is_export_jupyter_nominative_role(ROLE)),
            EXPORT_JUPYTER_PSEUDO: user_accesses.filter(Role.is_export_jupyter_pseudo_role(ROLE))}


def is_right_on_accesses(accesses: QuerySet, perimeter_ids: [int]):
    if accesses.filter(perimeter_id__in=perimeter_ids):
        return True
    return False


def get_max_perimeter_dict_right(perimeter: Perimeter, accesses: dict):
    above_levels_ids = get_perimeters_ids_list(perimeter.above_levels_ids)
    above_levels_ids.append(perimeter.id)
    perimeter_dict_right = {}
    for key, value in accesses.items():
        perimeter_dict_right[key] = is_right_on_accesses(accesses[key], above_levels_ids)
    return perimeter_dict_right


def get_right_default_dict():
    return {READ_PATIENT_NOMI: True,
            READ_PATIENT_PSEUDO: True,
            EXPORT_CSV_NOMI: True,
            EXPORT_CSV_PSEUDO: True,
            EXPORT_JUPYTER_NOMI: True,
            EXPORT_JUPYTER_PSEUDO: True}


def dict_boolean_and(dict_1: dict, dict_2: dict):
    and_dict = {}
    for key, value in dict_1.items():
        and_dict[key] = value and dict_2[key]
    return and_dict


def get_rights_from_cohort(accesses_dict: dict, cohort_ids_pop_source: list) -> dict:
    perimeters = Perimeter.objects.filter(cohort_id__in=cohort_ids_pop_source)
    right_dict = get_right_default_dict()
    for perimeter in perimeters:
        perimeter_right_dict = get_max_perimeter_dict_right(perimeter, accesses_dict)
        right_dict = dict_boolean_and(right_dict, perimeter_right_dict)
    return right_dict


def get_all_cohorts_rights(user_accesses: [Access], cohort_pop_source: dict):
    response_list = []
    accesses_dict = get_dict_right_accesses(user_accesses)
    for cohort_id, list_cohort_pop_source in cohort_pop_source.items():
        rights = get_rights_from_cohort(accesses_dict, list_cohort_pop_source)
        response_list.append(CohortRights(cohort_id, rights))

    return response_list


def psql_query_get_pop_source_from_cohort(cohorts_ids: list):
    return f"""
    SELECT fact_relationship_id,
    fact_id_1,
    fact_id_2
    FROM omop.fact_relationship
    WHERE delete_datetime IS NULL
    AND domain_concept_id_1 = 1147323
    AND domain_concept_id_2 = 1147323
    AND relationship_concept_id = 44818821
    AND fact_id_1 IN ({str(cohorts_ids)[1:-1]})
    """


def get_dict_cohort_pop_source(cohorts_ids: list):
    fact_relationships = FactRelationShip.objects.raw(psql_query_get_pop_source_from_cohort(cohorts_ids))
    cohort_pop_source = {}
    for fact in fact_relationships:
        if fact.fact_id_1 in cohort_pop_source:
            cohort_pop_source[fact.fact_id_1] = cohort_pop_source[fact.fact_id_1] + [fact.fact_id_2]
        else:
            cohort_pop_source[fact.fact_id_1] = [fact.fact_id_2]
    return cohort_pop_source


class CohortRights:
    def __init__(self, cohort_id, rights_dict, **kwargs):
        """
        @return: a default DataRight as required by the serializer
        """
        self.cohort_id = cohort_id
        self.rights = rights_dict


class FactRelationShip(models.Model):
    fact_relationship_id = models.BigIntegerField(primary_key=True)
    fact_id_1 = models.BigIntegerField()
    fact_id_2 = models.BigIntegerField()
    objects = OmopModelManager()

    class Meta:
        managed = False
        db_table = 'fact_relationship'
