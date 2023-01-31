import json
import logging
from collections import defaultdict
from typing import List

from coverage.annotate import os
from django.core.mail import EmailMultiAlternatives
from django.db import models
from django.db.models import QuerySet
from django.http import Http404

from accesses.conf_perimeters import OmopModelManager
from accesses.models import Perimeter, Access, Role
from admin_cohort.settings import EMAIL_SENDER_ADDRESS, FRONT_URL, EMAIL_SUPPORT_CONTACT
from cohort.models import CohortResult
from commons.tools import cast_string_to_ids_list
from exports.emails import get_base_templates, KEY_CONTENT, KEY_NAME, KEY_CONTACT_MAIL

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


def get_dict_right_accesses(user_accesses: [Access]) -> dict:
    """
    mapping for read patient, export CSV and transfer Jupyter right and list of accesses
    """
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
    above_levels_ids = cast_string_to_ids_list(perimeter.above_levels_ids)
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


def retrieve_perimeters(json_req: str) -> [str]:
    """
    Called to retrieve care_site_ids (perimeters) from a Json request
    :param json_req:
    :type json_req:
    :return:
    :rtype:
    """
    # sourcePopulation:{caresiteCohortList: [...ids]}
    try:
        req = json.loads(json_req)
        ids = req["sourcePopulation"]["caresiteCohortList"]
        assert isinstance(ids, list)
        str_ids = []
        for i in ids:
            str_ids.append(str(i))
            assert str(i).isnumeric()
        return str_ids
    except Exception:
        return None


_log = logging.getLogger('celery.app')


def log_count_task(dm_uuid, msg, global_estimate=False):
    _log.info(f"{'Global' if global_estimate else ''}Count Task [DM: {dm_uuid}] {msg}")


def log_create_task(cr_uuid, msg):
    _log.info(f"Cohort Create Task [CR: {cr_uuid}] {msg}")


def get_single_cohort_email_data(cohort_name, cohort_id):
    subject = "Votre cohorte est prête"
    cohort_link = f"{FRONT_URL}/cohort/{cohort_id}"
    html_body = f'Votre cohorte <a href="{cohort_link}">{cohort_name}</a> a été créée avec succès.'
    txt_body = f"Votre cohorte {cohort_name} a été créée avec succès. \n {cohort_link}"
    return subject, html_body, txt_body


def get_multi_cohort_email_data(cohorts):
    subject = "Vos cohortes sont prêtes"
    html_body = """ Vos cohortes ont été créées avec succès:
                    <br>
                    <ul>
                        KEY_COHORTS_ITEMS
                    </ul>
                """
    txt_body = """ Vos cohortes ont été créées avec succès:
                   KEY_COHORTS_ITEMS
               """
    html_items, txt_items = [], []
    for c in cohorts:
        cohort_name = c[0]
        cohort_link = f"{FRONT_URL}/cohort/{c[1]}"
        li = f'<li> <a href="{cohort_link}">{cohort_name}</a> </li>'
        html_items.append(li)

        item = f"- {cohort_name} {5*' '} {cohort_link}"
        txt_items.append(item)
    html_body = html_body.replace(KEY_COHORTS_ITEMS, "".join(html_items))
    txt_body = txt_body.replace(KEY_COHORTS_ITEMS, "\n".join(txt_items))
    return subject, html_body, txt_body


def send_email_notif_about_large_cohorts(fhir_group_ids: List[str]):
    # todo: group cohorts by user
    html_path = f"cohort/email_templates/large_cohorts_finished.html"
    txt_path = f"cohort/email_templates/large_cohorts_finished.txt"

    with open(html_path) as f:
        html_content = "\n".join(f.readlines())

    with open(txt_path) as f:
        txt_content = "\n".join(f.readlines())

    html_mail, txt_mail = get_base_templates()
    html_mail = html_mail.replace(KEY_CONTENT, html_content)
    txt_mail = txt_mail.replace(KEY_CONTENT, txt_content)

    cohorts_per_user = defaultdict(list)
    for c in CohortResult.objects.filter(fhir_group_id__in=fhir_group_ids):
        key = (f"{c.owner.firstname} {c.owner.lastname}", c.owner.email)
        cohorts_per_user[key].append((c.name, c.fhir_group_id))

    for user in cohorts_per_user:
        cohorts = cohorts_per_user[user]

        if len(cohorts) == 1:
            cohort_data = cohorts[0]
            subject, html_body, txt_body = get_single_cohort_email_data(*cohort_data)
        else:
            subject, html_body, txt_body = get_multi_cohort_email_data(cohorts=cohorts)

        user_fullname, user_email = user
        html_mail = html_mail.replace(KEY_NAME, user_fullname)\
                             .replace(KEY_EMAIL_BODY, html_body)\
                             .replace(KEY_CONTACT_MAIL, EMAIL_SUPPORT_CONTACT)
        txt_mail = txt_mail.replace(KEY_NAME, user_fullname)\
                           .replace(KEY_EMAIL_BODY, txt_body)\
                           .replace(KEY_CONTACT_MAIL, EMAIL_SUPPORT_CONTACT)

        msg = EmailMultiAlternatives(subject=subject,
                                     body=txt_mail,
                                     from_email=EMAIL_SENDER_ADDRESS,
                                     to=[user_email])
        msg.attach_alternative(content=html_mail, mimetype="text/html")
        msg.attach_file('exports/email_templates/logoCohort360.png')
        msg.send()
