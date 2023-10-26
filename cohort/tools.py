import json
import logging

from coverage.annotate import os
from django.db import models
from django.db.models import QuerySet
from django.http import Http404
from rest_framework.request import Request

from accesses.conf_perimeters import OmopModelManager
from accesses.models import Perimeter, Access, Role
from admin_cohort.settings import SJS_USERNAME, ETL_USERNAME
from cohort.models import CohortResult

ROLE = "role"
READ_PATIENT_NOMI = "read_patient_nomi"
READ_PATIENT_PSEUDO = "read_patient_pseudo"
EXPORT_CSV_NOMI = "export_csv_nomi"
EXPORT_CSV_PSEUDO = "export_csv_pseudo"
EXPORT_JUPYTER_NOMI = "export_jupyter_nomi"
EXPORT_JUPYTER_PSEUDO = "export_jupyter_pseudo"
SEARCH_IPP = "search_ipp"

KEY_COHORTS_ITEMS = "KEY_COHORTS_ITEMS"
KEY_EMAIL_BODY = "KEY_EMAIL_BODY"

env = os.environ
_logger_err = logging.getLogger('django.request')


def is_sjs_or_etl_user(request: Request):
    return request.method in ("GET", "PATCH") and \
           request.user.is_authenticated and \
           request.user.provider_username in [SJS_USERNAME, ETL_USERNAME]


def is_sjs_user(request: Request):
    return is_sjs_or_etl_user(request=request)


def get_dict_right_accesses(user_accesses: [Access]) -> dict:
    """
    mapping for read patient, export CSV and transfer Jupyter right and list of accesses
    """
    return {READ_PATIENT_NOMI: user_accesses.filter(Role.q_allow_read_patient_data_nominative()),
            READ_PATIENT_PSEUDO: user_accesses.filter(Role.q_allow_read_patient_data_pseudo() |
                                                      Role.q_allow_read_patient_data_nominative()),  # was: Role.q_allow_read_patient_data()
            EXPORT_CSV_NOMI: user_accesses.filter(Role.q_allow_export_csv_nominative()),
            EXPORT_CSV_PSEUDO: user_accesses.filter(Role.q_allow_export_csv_pseudo()),
            EXPORT_JUPYTER_NOMI: user_accesses.filter(Role.q_allow_export_jupyter_nominative()),
            EXPORT_JUPYTER_PSEUDO: user_accesses.filter(Role.q_allow_export_jupyter_pseudo())}


def is_right_on_accesses(accesses: QuerySet, perimeter_ids: [int]):
    if accesses.filter(perimeter_id__in=perimeter_ids):
        return True
    return False


def get_max_perimeter_dict_right(perimeter: Perimeter, accesses: dict):
    above_levels_ids = perimeter.above_levels
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
    """
    For cohort pop source and user accesses mapping give dict of cohort right boolean
    """
    perimeters = Perimeter.objects.filter(cohort_id__in=cohort_ids_pop_source)
    right_dict = get_right_default_dict()
    for perimeter in perimeters:
        perimeter_right_dict = get_max_perimeter_dict_right(perimeter, accesses_dict)
        right_dict = dict_boolean_and(right_dict, perimeter_right_dict)
    return right_dict


def get_all_cohorts_rights(user_accesses: [Access], cohort_pop_source: dict):
    """
    Return list of CohortRights => dict of boolean right aggregation for cohort perimeter pop source
    """
    response_list = []
    accesses_dict = get_dict_right_accesses(user_accesses)
    for cohort_id, list_cohort_pop_source in cohort_pop_source.items():
        rights = get_rights_from_cohort(accesses_dict, list_cohort_pop_source)
        response_list.append(CohortRights(cohort_id, rights))

    return response_list


def psql_query_get_pop_source_from_cohort(cohorts_ids: list):
    """
    @param cohorts_ids: cohort id source
    @return: mapping of cohort source in fact_id_1 and cohort id of care site (Perimeters) in fact_id_2
    """
    domain_concept_id = env.get("DOMAIN_CONCEPT_COHORT")  # 1147323
    relationship_concept_id = env.get("FACT_RELATIONSHIP_CONCEPT_COHORT")  # 44818821
    return f"""
    SELECT row_id,
    fact_id_1,
    fact_id_2
    FROM omop.fact_relationship
    WHERE delete_datetime IS NULL
    AND domain_concept_id_1 = {domain_concept_id}
    AND domain_concept_id_2 = {domain_concept_id}
    AND relationship_concept_id = {relationship_concept_id}
    AND fact_id_1 IN ({str(cohorts_ids)[1:-1]})
    """


def get_list_cohort_id_care_site(cohorts_ids: list, all_user_cohorts: [CohortResult]):
    """
    Give the list of cohort_id and the list of Perimete.cohort_id population source for cohort users and remove
    cohort user ids
    """
    fact_relationships = FactRelationShip.objects.raw(psql_query_get_pop_source_from_cohort(cohorts_ids))
    cohort_pop_source = cohorts_ids.copy()
    for fact in fact_relationships:
        if len(all_user_cohorts.filter(fhir_group_id=fact.fact_id_1)) == 0:
            raise Http404(f"Issue in cohort's belonging user: {fact.fact_id_1} is not user cohort")
        if fact.fact_id_1 in cohort_pop_source:
            cohort_pop_source.remove(fact.fact_id_1)
        cohort_pop_source.append(fact.fact_id_2)
    return cohort_pop_source


def get_dict_cohort_pop_source(cohorts_ids: list):
    """
    Give the mapping of cohort_id and the list of Perimete.cohort_id population source for this cohort
    """
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
    row_id = models.BigIntegerField(primary_key=True)
    fact_id_1 = models.BigIntegerField()
    fact_id_2 = models.BigIntegerField()
    objects = OmopModelManager()

    class Meta:
        managed = False
        db_table = 'fact_relationship'


def retrieve_perimeters(json_query: str) -> [str]:
    try:
        query = json.loads(json_query)
        perimeters_ids = query["sourcePopulation"]["caresiteCohortList"]
        assert all(i.isnumeric() for i in perimeters_ids), "Perimeters ids must be integers"
        return perimeters_ids
    except json.JSONDecodeError as e:
        _logger_err.exception(f"Error extracting perimeters ids from JSON query - {e}")
        raise


_celery_logger = logging.getLogger('celery.app')


def log_count_task(dm_uuid, msg, global_estimate=False):
    _celery_logger.info(f"{'Global' if global_estimate else ''}Count Task [DM: {dm_uuid}] {msg}")


def log_count_all_task(dm_uuid, msg):
    _celery_logger.info(f"Global Count Task [DM: {dm_uuid}] {msg}")


def log_create_task(cr_uuid, msg):
    _celery_logger.info(f"Cohort Create Task [CR: {cr_uuid}] {msg}")


def log_delete_task(cr_uuid, msg):
    _celery_logger.info(f"Cohort Delete Task [CR: {cr_uuid}] {msg}")
