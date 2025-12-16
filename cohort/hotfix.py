from __future__ import annotations

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import connection, transaction
from django.db.models import Q
from django.utils import timezone

from accesses_perimeters.models import ListCohort
from cohort.models import RequestQuerySnapshot
from cohort.services.request_query_snapshot import RequestQuerySnapshotService
from cohort.models.cohort_result import CohortResult
from cohort.models.request import Request
from admin_cohort.models.user import User
from cohort.models.dated_measure import DatedMeasure

date_input_limit = "2025-08-15"


def _get_owner_from_user_aph_id(user_aph_id: str):
    try:
        return User.objects.get(pk=user_aph_id)
    except User.DoesNotExist:
        pass

    try:
        return User.objects.get(username=user_aph_id)
    except User.DoesNotExist as e:
        raise ValueError(f"No User found for user_aph_id={user_aph_id}") from e


def patch():
    list_listcohort = ListCohort.get_practitioner_patient_lists_since(date_input_limit)
    list_cohort = list_listcohort[0]
    user_aph_id = list_cohort._sourcereferenceid

    cohort_date = str(list_cohort.insert_datetime)[0:16].strip()  # '2025-01-01 10:45'
    cohort_group_id = list_cohort.id
    cohort_json_query = list_cohort.note___query__text
    cohort_user = _get_owner_from_user_aph_id(user_aph_id=user_aph_id)
    cohort_name = f"Cohorte du {cohort_date}"
    cohort_description = f"Cohorte backup omop du practitioner {user_aph_id} créée le {cohort_date}"
    cohort_size = list_cohort._size

    with transaction.atomic():
        req = Request.objects.create(
            owner=cohort_user,
            name=cohort_name,
            description="Request créée via hotfix (backup OMOP)",
        )

        rqs = RequestQuerySnapshot.objects.create(
            owner=cohort_user,
            request=req,
            serialized_query=cohort_json_query,
            perimeters_ids=RequestQuerySnapshotService.retrieve_perimeters(json_query=cohort_json_query),
            version=1,
            name=cohort_name,
        )

        dm = DatedMeasure.objects.create(
            owner=cohort_user,
            request_query_snapshot=rqs,
            fhir_datetime=timezone.now(),
            measure=cohort_size,
            measure_min=cohort_size,
            measure_max=cohort_size,
        )

        cohort_result = CohortResult.objects.create(
            owner=cohort_user,
            name=cohort_name,
            group_id=str(cohort_group_id),
            request_query_snapshot=rqs,
            dated_measure=dm,
            description=(cohort_description),
        )

    return cohort_result
