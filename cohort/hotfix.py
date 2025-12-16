from __future__ import annotations

import json
from typing import List

from django.db import transaction
from django.utils import timezone

from accesses_perimeters.apps import AccessesPerimetersConfig
from accesses_perimeters.models import ListCohort
from admin_cohort.types import JobStatus
from cohort.models import RequestQuerySnapshot, Folder
from cohort.models.cohort_result import CohortResult
from cohort.models.request import Request
from admin_cohort.models.user import User
from cohort.models.dated_measure import DatedMeasure


def _get_owner_from_user_aph_id(user_aph_id: str):
    try:
        return User.objects.get(pk=user_aph_id)
    except User.DoesNotExist:
        pass
    try:
        return User.objects.get(username=user_aph_id)
    except User.DoesNotExist as e:
        raise ValueError(f"No User found for user_aph_id={user_aph_id}") from e


def _retrieve_perimeters_hotfix(json_query: str) -> List[str]:
    try:
        query = json.loads(json_query)
        perimeters_ids = query["sourcePopulation"]["caresiteCohortList"]
        if not isinstance(perimeters_ids, list):
            raise TypeError("caresiteCohortList must be a list")
        normalized: List[str] = []
        for i in perimeters_ids:
            if isinstance(i, int):
                normalized.append(str(i))
            elif isinstance(i, str) and i.isnumeric():
                normalized.append(i)
            else:
                raise ValueError(f"Invalid perimeter id: {i!r}")
        return normalized
    except (json.JSONDecodeError, TypeError, KeyError, ValueError) as e:
        raise ValueError(f"Error extracting perimeters ids from JSON query - {e}") from e


def _get_practitioner_patient_lists_since(since_dt: str):
    # IMPORTANT: exécuter sur la DB où le schéma `omop` existe (même DB que perimeters_updater).
    db_alias = AccessesPerimetersConfig.DB_ALIAS
    sql = f"""
              SELECT *
              FROM omop.list
              WHERE source__type = 'Practitioner'
                AND subject__type = 'Patient'
                AND insert_datetime >= '{since_dt}'
                AND delete_datetime IS NULL
                AND _size > 0;
              """
    return ListCohort.objects.using(db_alias).raw(sql)


def _debug(msg: str) -> None:
    print(f"[hotfix.patch] {msg}")


def patch_cohort_test(date_input_limit: str, specify_user: str = None):
    _debug(f"START patch(date_input_limit={date_input_limit!r})")
    list_listcohort = _get_practitioner_patient_lists_since(date_input_limit)
    _debug(f"ListCohort fetched: count={len(list_listcohort)}")
    if not list_listcohort:
        _debug(f"No ListCohort found -> raising ValueError (date_input_limit={date_input_limit!r})")
        raise ValueError(f"No ListCohort found since date_input_limit={date_input_limit!r}")
    list_cohort = list_listcohort[0]
    _debug(
        f"Using first ListCohort: id={getattr(list_cohort, 'id', None)!r}, insert_datetime={getattr(list_cohort, 'insert_datetime', None)!r}, _sourcereferenceid={getattr(list_cohort, '_sourcereferenceid', None)!r}, _size={getattr(list_cohort, '_size', None)!r}")
    user_aph_id = specify_user if specify_user else list_cohort._sourcereferenceid
    cohort_date = str(list_cohort.insert_datetime)[0:16].strip()
    cohort_group_id = list_cohort.id
    cohort_json_query = list_cohort.note_query_text
    _debug(f"cohort_date={cohort_date!r}")
    _debug(f"cohort_group_id={cohort_group_id!r}")
    _debug(
        f"cohort_json_query: type={type(cohort_json_query).__name__}, length={len(cohort_json_query) if cohort_json_query else 0}")
    cohort_user = _get_owner_from_user_aph_id(user_aph_id=user_aph_id)
    _debug(
        f"Resolved owner user: id={getattr(cohort_user, 'pk', None)!r}, username={getattr(cohort_user, 'username', None)!r}")
    cohort_name = f"Cohorte du {cohort_date}"
    cohort_description = f"Cohorte backup omop du practitioner {user_aph_id} créée le {cohort_date}"
    cohort_size = list_cohort._size
    _debug(f"cohort_name={cohort_name!r}")
    _debug(f"cohort_description={cohort_description!r}")
    _debug(f"cohort_size={cohort_size!r}")
    _debug("Entering transaction.atomic()")
    with transaction.atomic():
        _debug("Getting/Creating Folder ...")
        folder_name = "Cohortes de fin 2025"
        folder_description = "backup de cohortes de fin 2025"
        folder, created = Folder.objects.get_or_create(
            owner=cohort_user,
            name=folder_name,
            defaults={"description": folder_description},
        )
        if created:
            _debug(
                f"Folder created: pk={getattr(folder, 'pk', None)!r}, "
                f"uuid={getattr(folder, 'uuid', None)!r}, name={getattr(folder, 'name', None)!r}"
            )
        else:
            _debug(
                f"Folder found: pk={getattr(folder, 'pk', None)!r}, "
                f"uuid={getattr(folder, 'uuid', None)!r}, name={getattr(folder, 'name', None)!r}"
            )
        _debug("Creating Request ...")
        req = Request.objects.create(
            owner=cohort_user,
            parent_folder=folder,
            name=f"Nouvelle requête n ({cohort_name})",
            description=f"Request issue de la cohorte ({cohort_name})",
        )
        _debug(
            f"Request created: pk={getattr(req, 'pk', None)!r}, uuid={getattr(req, 'uuid', None)!r}, name={getattr(req, 'name', None)!r}")
        _debug("Computing perimeters_ids from json_query ...")
        perimeters_ids = _retrieve_perimeters_hotfix(json_query=cohort_json_query)
        try:
            perimeters_len = len(perimeters_ids)
        except TypeError:
            perimeters_len = None
        _debug(
            f"perimeters_ids computed: type={type(perimeters_ids).__name__}, len={perimeters_len}, value={perimeters_ids!r}")
        _debug("Creating RequestQuerySnapshot ...")
        rqs = RequestQuerySnapshot.objects.create(
            owner=cohort_user,
            request=req,
            serialized_query=cohort_json_query,
            perimeters_ids=perimeters_ids,
            version=1,
            name=cohort_name,
        )
        _debug(
            f"RequestQuerySnapshot created: pk={getattr(rqs, 'pk', None)!r}, uuid={getattr(rqs, 'uuid', None)!r}, version={getattr(rqs, 'version', None)!r}")
        now = timezone.now()
        _debug(f"Creating DatedMeasure ... fhir_datetime={now!r}")
        dm = DatedMeasure.objects.create(
            owner=cohort_user,
            request_query_snapshot=rqs,
            fhir_datetime=now,
            measure=cohort_size,
            measure_min=cohort_size,
            measure_max=cohort_size,
            request_job_status=JobStatus.finished,
        )
        _debug(
            f"DatedMeasure created: pk={getattr(dm, 'pk', None)!r}, uuid={getattr(dm, 'uuid', None)!r}, measure={getattr(dm, 'measure', None)!r}")
        _debug("Creating CohortResult ...")
        cohort_result = CohortResult.objects.create(
            owner=cohort_user,
            name=cohort_name,
            group_id=str(cohort_group_id),
            request_query_snapshot=rqs,
            dated_measure=dm,
            description=cohort_description,
            request_job_status=JobStatus.finished,
        )
        _debug(
            f"CohortResult created: pk={getattr(cohort_result, 'pk', None)!r}, uuid={getattr(cohort_result, 'uuid', None)!r}, group_id={getattr(cohort_result, 'group_id', None)!r}")
    _debug("END patch() - returning cohort_result")
    return cohort_result

# patch_cohort("2025-07-21")
