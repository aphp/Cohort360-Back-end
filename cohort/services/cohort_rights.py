from dataclasses import dataclass
from typing import List

from django.db import IntegrityError
from django.db.models import QuerySet
from django.http import Http404

from accesses.models import Perimeter
from accesses.q_expressions import q_allow_read_patient_data_nominative, q_allow_read_patient_data_pseudo, q_allow_export_csv_nominative, \
    q_allow_export_csv_pseudo, q_allow_export_jupyter_nominative, q_allow_export_jupyter_pseudo
from accesses.services.accesses import accesses_service
from admin_cohort.models import User
from cohort.models import CohortResult

ROLE = "role"
READ_PATIENT_NOMI = "read_patient_nomi"
READ_PATIENT_PSEUDO = "read_patient_pseudo"
EXPORT_CSV_NOMI = "export_csv_nomi"
EXPORT_CSV_PSEUDO = "export_csv_pseudo"
EXPORT_JUPYTER_NOMI = "export_jupyter_nomi"
EXPORT_JUPYTER_PSEUDO = "export_jupyter_pseudo"


def all_true_rights():
    return {READ_PATIENT_NOMI: True,
            READ_PATIENT_PSEUDO: True,
            EXPORT_CSV_NOMI: True,
            EXPORT_CSV_PSEUDO: True,
            EXPORT_JUPYTER_NOMI: True,
            EXPORT_JUPYTER_PSEUDO: True
            }


@dataclass
class CohortRights:
    cohort_id: str
    rights: dict


class CohortRightsService:

    def get_user_rights_on_cohorts(self, group_ids: str, user: User) -> List[dict]:
        group_ids = [i.strip() for i in group_ids.split(",") if i]
        if not CohortResult.objects.filter(group_id__in=group_ids).exists():
            raise Http404("No cohorts found. The provided `group_id`s are not valid")
        user_accesses = accesses_service.get_user_valid_accesses(user=user)
        if not user_accesses:
            raise Http404(f"The user `{user}` has no valid accesses")
        cohort_perimeters = self.get_cohort_perimeters(cohorts_ids=group_ids, owner=user)
        accesses_per_right = self.get_accesses_per_right(user_accesses=user_accesses)
        cohort_rights = []

        for cohort_id, perimeters in cohort_perimeters.items():
            rights = self.get_rights_on_perimeters(accesses_per_right=accesses_per_right,
                                                   perimeters=perimeters)
            cohort_rights.append(CohortRights(cohort_id, rights).__dict__)
        return cohort_rights

    def get_cohort_perimeters(self, cohorts_ids: List[str], owner: User) -> dict[str, QuerySet[Perimeter]]:
        cohorts_owners = CohortResult.objects.filter(group_id__in=cohorts_ids)\
                                             .values_list("owner_id", flat=True)\
                                             .distinct()
        if cohorts_owners.count() != 1 or owner.username not in cohorts_owners:
            raise IntegrityError(f"One or multiple cohorts with given IDs do not belong to user '{owner.display_name}'")
        virtual_cohorts = self.retrieve_virtual_cohorts_ids_from_snapshot(cohorts_ids=cohorts_ids) or {}
        return {cohort_id: Perimeter.objects.filter(cohort_id__in=virtual_cohort_ids)
                for cohort_id, virtual_cohort_ids in virtual_cohorts.items()}

    @staticmethod
    def retrieve_virtual_cohorts_ids_from_snapshot(cohorts_ids: List[str]) -> dict[str, List[str]]:
        cohorts = CohortResult.objects.filter(group_id__in=cohorts_ids)
        return {cohort.group_id: cohort.request_query_snapshot.perimeters_ids for cohort in cohorts}

    @staticmethod
    def get_accesses_per_right(user_accesses: QuerySet) -> dict[str, QuerySet]:
        return {READ_PATIENT_NOMI: user_accesses.filter(q_allow_read_patient_data_nominative),
                READ_PATIENT_PSEUDO: user_accesses.filter(q_allow_read_patient_data_pseudo |
                                                          q_allow_read_patient_data_nominative),
                EXPORT_CSV_NOMI: user_accesses.filter(q_allow_export_csv_nominative),
                EXPORT_CSV_PSEUDO: user_accesses.filter(q_allow_export_csv_pseudo),
                EXPORT_JUPYTER_NOMI: user_accesses.filter(q_allow_export_jupyter_nominative),
                EXPORT_JUPYTER_PSEUDO: user_accesses.filter(q_allow_export_jupyter_pseudo)}

    @staticmethod
    def get_rights_on_perimeters(accesses_per_right: dict, perimeters: QuerySet[Perimeter]) -> dict[str, bool]:
        rights = all_true_rights()
        for perimeter in perimeters:
            perimeter_and_above = [perimeter.id] + perimeter.above_levels
            for r in rights:
                accesses = accesses_per_right[r]
                is_valid_right = accesses.filter(perimeter_id__in=perimeter_and_above).exists()
                rights[r] = rights[r] and is_valid_right
        return rights


cohort_rights_service = CohortRightsService()
