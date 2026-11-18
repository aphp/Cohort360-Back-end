import logging
from dataclasses import dataclass
from typing import List, Optional

from django.db.models import QuerySet
from django.http import Http404

from accesses.models import Perimeter
from accesses.q_expressions import (
    q_allow_read_patient_data_nominative,
    q_allow_read_patient_data_pseudo,
    q_allow_export_csv_xlsx_nominative,
    q_allow_export_jupyter_nominative,
    q_allow_export_jupyter_pseudo,
)
from accesses.porthab import porthab_read_perimeter_ids, porthab_rights
from accesses.services.accesses import accesses_service
from admin_cohort.models import User
from cohort.models import CohortResult

logger = logging.getLogger(__name__)

ROLE = "role"
READ_PATIENT_NOMI = "read_patient_nomi"
READ_PATIENT_PSEUDO = "read_patient_pseudo"
EXPORT_CSV_XLSX_NOMI = "export_csv_xlsx_nomi"
EXPORT_JUPYTER_NOMI = "export_jupyter_nomi"
EXPORT_JUPYTER_PSEUDO = "export_jupyter_pseudo"


def all_true_rights():
    return {READ_PATIENT_NOMI: True, READ_PATIENT_PSEUDO: True, EXPORT_CSV_XLSX_NOMI: True, EXPORT_JUPYTER_NOMI: True, EXPORT_JUPYTER_PSEUDO: True}


@dataclass
class CohortRights:
    cohort_id: str
    rights: dict


class CohortRightsService:
    def get_user_rights_on_cohorts(self, group_ids: str, user: User) -> List[dict]:
        group_id_list = [i.strip() for i in group_ids.split(",") if i]
        if not CohortResult.objects.filter(group_id__in=group_id_list).exists():
            raise Http404("No cohorts found. The provided `group_id`s are not valid")
        user_accesses = accesses_service.get_user_valid_accesses(user=user)
        if not user_accesses and not any(porthab_read_perimeter_ids(user)):
            raise Http404(f"The user `{user}` has no valid accesses")
        cohort_perimeters = self.get_cohort_perimeters(cohorts_ids=group_id_list, owner=user)
        perimeter_ids_per_right = self.get_perimeter_ids_per_right(user=user, user_accesses=user_accesses)
        cohort_rights = []

        for cohort_id, perimeters in cohort_perimeters.items():
            rights = self.get_rights_on_perimeters(perimeter_ids_per_right=perimeter_ids_per_right, perimeters=perimeters)
            cohort_rights.append(CohortRights(cohort_id, rights).__dict__)
        return cohort_rights

    def get_cohort_perimeters(self, cohorts_ids: List[str], owner: User) -> dict[str, QuerySet[Perimeter]]:
        cohorts = CohortResult.objects.filter(group_id__in=cohorts_ids)
        owned_cohorts_ids = set(cohorts.filter(owner=owner).values_list("group_id", flat=True))
        other_owners_cohorts_ids = set(cohorts.exclude(owner=owner).values_list("group_id", flat=True))
        if other_owners_cohorts_ids:
            logger.warning("Ignoring cohorts of other owners for user %s - group_ids: %s", owner.username, sorted(other_owners_cohorts_ids))
        if not owned_cohorts_ids:
            raise Http404("No cohorts found. The provided `group_id`s are not valid")
        virtual_cohorts = self.retrieve_virtual_cohorts_ids_from_snapshot(cohorts_ids=list(owned_cohorts_ids), owner=owner) or {}
        return {cohort_id: Perimeter.objects.filter(cohort_id__in=virtual_cohort_ids) for cohort_id, virtual_cohort_ids in virtual_cohorts.items()}

    @staticmethod
    def retrieve_virtual_cohorts_ids_from_snapshot(cohorts_ids: List[str], owner: Optional[User] = None) -> dict[str, List[str]]:
        cohorts = CohortResult.objects.filter(group_id__in=cohorts_ids)
        if owner is not None:
            cohorts = cohorts.filter(owner=owner)
        out: dict[str, list[str]] = {}
        for c in cohorts:
            snap = c.request_query_snapshot
            pids: list[str] = []
            if snap is not None and snap.perimeters_ids is not None:
                pids = list(snap.perimeters_ids)
            if owner is None:
                out[c.group_id] = pids  # original behavior: the last cohort read wins
            else:
                # merge the perimeters of the owner's cohorts sharing the same group_id
                previous_perimeters_ids = out.get(c.group_id, [])
                out[c.group_id] = previous_perimeters_ids + [p for p in pids if p not in previous_perimeters_ids]
        return out

    @staticmethod
    def get_perimeter_ids_per_right(user: User, user_accesses: QuerySet) -> dict[str, set[int]]:
        natives = {
            READ_PATIENT_NOMI: user_accesses.filter(q_allow_read_patient_data_nominative),
            READ_PATIENT_PSEUDO: user_accesses.filter(q_allow_read_patient_data_pseudo | q_allow_read_patient_data_nominative),
            EXPORT_CSV_XLSX_NOMI: user_accesses.filter(q_allow_export_csv_xlsx_nominative),
            EXPORT_JUPYTER_NOMI: user_accesses.filter(q_allow_export_jupyter_nominative),
            EXPORT_JUPYTER_PSEUDO: user_accesses.filter(q_allow_export_jupyter_pseudo),
        }
        ids = {right: set(accesses.values_list("perimeter_id", flat=True)) for right, accesses in natives.items()}
        nomi, pseudo = porthab_read_perimeter_ids(user)
        rights = porthab_rights(user)
        ids[READ_PATIENT_NOMI] |= nomi
        ids[READ_PATIENT_PSEUDO] |= nomi | pseudo
        if "right_export_csv_xlsx_nominative" in rights:
            ids[EXPORT_CSV_XLSX_NOMI] |= nomi
        if "right_export_jupyter_nominative" in rights:
            ids[EXPORT_JUPYTER_NOMI] |= nomi
        if "right_export_jupyter_pseudonymized" in rights:
            ids[EXPORT_JUPYTER_PSEUDO] |= nomi | pseudo
        return ids

    @staticmethod
    def get_rights_on_perimeters(perimeter_ids_per_right: dict[str, set[int]], perimeters: QuerySet[Perimeter]) -> dict[str, bool]:
        rights = all_true_rights()
        for perimeter in perimeters:
            perimeter_and_above = [perimeter.id] + perimeter.above_levels
            for r in rights:
                rights[r] = rights[r] and any(p in perimeter_ids_per_right[r] for p in perimeter_and_above)
        return rights


cohort_rights_service = CohortRightsService()
