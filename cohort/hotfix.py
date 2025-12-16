from __future__ import annotations

from django.db import transaction
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
    def _debug(msg: str) -> None:
        print(f"[hotfix.patch] {msg}")

    _debug(f"START patch(date_input_limit={date_input_limit!r})")

    list_listcohort = ListCohort.get_practitioner_patient_lists_since(date_input_limit)
    _debug(f"ListCohort fetched: count={len(list_listcohort)}")

    if not list_listcohort:
        _debug("No ListCohort found -> raising ValueError")
        raise ValueError(f"No ListCohort found since date_input_limit={date_input_limit!r}")

    list_cohort = list_listcohort[0]
    _debug(
        "Using first ListCohort: "
        f"id={getattr(list_cohort, 'id', None)!r}, "
        f"insert_datetime={getattr(list_cohort, 'insert_datetime', None)!r}, "
        f"_sourcereferenceid={getattr(list_cohort, '_sourcereferenceid', None)!r}, "
        f"_size={getattr(list_cohort, '_size', None)!r}"
    )

    user_aph_id = list_cohort._sourcereferenceid

    cohort_date = str(list_cohort.insert_datetime)[0:16].strip()  # '2025-01-01 10:45'
    cohort_group_id = list_cohort.id
    cohort_json_query = list_cohort.note___query__text
    _debug(f"cohort_date={cohort_date!r}")
    _debug(f"cohort_group_id={cohort_group_id!r}")
    _debug(
        f"cohort_json_query: type={type(cohort_json_query).__name__}, length={len(cohort_json_query) if cohort_json_query else 0}")

    cohort_user = _get_owner_from_user_aph_id(user_aph_id=user_aph_id)
    _debug(
        "Resolved owner user: "
        f"id={getattr(cohort_user, 'pk', None)!r}, "
        f"username={getattr(cohort_user, 'username', None)!r}"
    )

    cohort_name = f"Cohorte du {cohort_date}"
    cohort_description = f"Cohorte backup omop du practitioner {user_aph_id} créée le {cohort_date}"
    cohort_size = list_cohort._size
    _debug(f"cohort_name={cohort_name!r}")
    _debug(f"cohort_description={cohort_description!r}")
    _debug(f"cohort_size={cohort_size!r}")

    _debug("Entering transaction.atomic()")
    with transaction.atomic():
        _debug("Creating Request ...")
        req = Request.objects.create(
            owner=cohort_user,
            name=cohort_name,
            description="Request créée via hotfix (backup OMOP)",
        )
        _debug(
            "Request created: "
            f"pk={getattr(req, 'pk', None)!r}, "
            f"uuid={getattr(req, 'uuid', None)!r}, "
            f"name={getattr(req, 'name', None)!r}"
        )

        _debug("Computing perimeters_ids from json_query ...")
        perimeters_ids = RequestQuerySnapshotService.retrieve_perimeters(json_query=cohort_json_query)
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
            "RequestQuerySnapshot created: "
            f"pk={getattr(rqs, 'pk', None)!r}, "
            f"uuid={getattr(rqs, 'uuid', None)!r}, "
            f"version={getattr(rqs, 'version', None)!r}"
        )

        now = timezone.now()
        _debug(f"Creating DatedMeasure ... fhir_datetime={now!r}")
        dm = DatedMeasure.objects.create(
            owner=cohort_user,
            request_query_snapshot=rqs,
            fhir_datetime=now,
            measure=cohort_size,
            measure_min=cohort_size,
            measure_max=cohort_size,
        )
        _debug(
            "DatedMeasure created: "
            f"pk={getattr(dm, 'pk', None)!r}, "
            f"uuid={getattr(dm, 'uuid', None)!r}, "
            f"measure={getattr(dm, 'measure', None)!r}"
        )

        _debug("Creating CohortResult ...")
        cohort_result = CohortResult.objects.create(
            owner=cohort_user,
            name=cohort_name,
            group_id=str(cohort_group_id),
            request_query_snapshot=rqs,
            dated_measure=dm,
            description=(cohort_description),
        )
        _debug(
            "CohortResult created: "
            f"pk={getattr(cohort_result, 'pk', None)!r}, "
            f"uuid={getattr(cohort_result, 'uuid', None)!r}, "
            f"group_id={getattr(cohort_result, 'group_id', None)!r}"
        )

    _debug("END patch() - returning cohort_result")
    return cohort_result
