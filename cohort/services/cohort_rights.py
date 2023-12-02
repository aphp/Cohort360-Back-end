from dataclasses import dataclass
from collections import defaultdict
from typing import List

from django.db.models import QuerySet
from django.http import Http404

from accesses.conf_perimeters import FactRelationShip
from accesses.models import Role, Perimeter, get_user_valid_manual_accesses
from admin_cohort.models import User


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

    def get_user_rights_on_cohorts(self, cohorts: QuerySet, user: User) -> List[dict]:
        if not cohorts:
            raise Http404("No cohorts found. The provided `fhir_group_id`s are not valid")
        user_accesses = get_user_valid_manual_accesses(user=user)
        if not user_accesses:
            raise Http404(f"The user `{user}` has no valid accesses")
        cohort_ids = cohorts.filter(fhir_group_id__isnull=False)\
                            .values_list("fhir_group_id", flat=True)
        cohort_perimeters = self.get_cohort_perimeters(cohort_ids=cohort_ids)
        accesses_per_right = self.get_accesses_per_right(user_accesses=user_accesses)
        cohort_rights = []

        for cohort_id, perimeters in cohort_perimeters.items():
            rights = self.get_rights_on_perimeters(accesses_per_right=accesses_per_right,
                                                   perimeters=perimeters)
            cohort_rights.append(CohortRights(cohort_id, rights).__dict__)
        return cohort_rights

    @staticmethod
    def get_cohort_perimeters(cohort_ids: List[str]) -> dict[str, List[Perimeter]]:
        fact_relationships = FactRelationShip.objects.raw(raw_query=FactRelationShip.psql_query_get_cohort_population_source(cohort_ids))
        cohort_perimeters = defaultdict(list)
        for fact in fact_relationships:
            try:
                perimeter = Perimeter.objects.get(cohort_id=fact.fact_id_2)
            except Perimeter.DoesNotExist:
                continue
            cohort_perimeters[fact.fact_id_1].append(perimeter)
        return cohort_perimeters

    @staticmethod
    def get_accesses_per_right(user_accesses: QuerySet) -> dict[str, QuerySet]:
        return {READ_PATIENT_NOMI: user_accesses.filter(Role.is_read_patient_role_nominative(ROLE)),
                READ_PATIENT_PSEUDO: user_accesses.filter(Role.is_read_patient_role(ROLE)),
                EXPORT_CSV_NOMI: user_accesses.filter(Role.is_export_csv_nominative_role(ROLE)),
                EXPORT_CSV_PSEUDO: user_accesses.filter(Role.is_export_csv_pseudo_role(ROLE)),
                EXPORT_JUPYTER_NOMI: user_accesses.filter(Role.is_export_jupyter_nominative_role(ROLE)),
                EXPORT_JUPYTER_PSEUDO: user_accesses.filter(Role.is_export_jupyter_pseudo_role(ROLE))
                }

    @staticmethod
    def get_rights_on_perimeters(accesses_per_right: dict, perimeters: List[Perimeter]) -> dict[str, bool]:
        rights = all_true_rights()
        for perimeter in perimeters:
            perimeter_and_above = [perimeter.id] + perimeter.above_levels
            for r in rights:
                accesses = accesses_per_right[r]
                is_valid_right = accesses.filter(perimeter_id__in=perimeter_and_above).exists()
                rights[r] = rights[r] and is_valid_right
        return rights


cohort_rights_service = CohortRightsService()