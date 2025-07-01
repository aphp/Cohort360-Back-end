from functools import lru_cache

from django.db.models import Q

from accesses.models import Right
from admin_cohort.tools import join_qs


q_allow_read_patient_data_nominative = Q(role__right_read_patient_nominative=True)
q_allow_read_patient_data_pseudo = Q(role__right_read_patient_pseudonymized=True)
q_allow_search_patients_by_ipp = Q(role__right_search_patients_by_ipp=True)
q_allow_unlimited_patients_search = Q(role__right_search_patients_unlimited=True)
q_allow_read_search_opposed_patient_data = Q(role__right_search_opposed_patients=True)
q_allow_export_csv_xlsx_nominative = Q(role__right_export_csv_xlsx_nominative=True)
q_allow_export_jupyter_nominative = Q(role__right_export_jupyter_nominative=True)
q_allow_export_jupyter_pseudo = join_qs([Q(role__right_export_jupyter_nominative=True),
                                         Q(role__right_export_jupyter_pseudonymized=True)])


@lru_cache(maxsize=None)
def q_allow_manage_accesses_on_same_level() -> Q:
    return join_qs([Q(**{f'role__{right.name}': True})
                    for right in Right.objects.filter(allow_edit_accesses_on_same_level=True)])


@lru_cache(maxsize=None)
def q_allow_manage_accesses_on_inf_levels() -> Q:
    return join_qs([Q(**{f'role__{right.name}': True})
                    for right in Right.objects.filter(allow_edit_accesses_on_inf_levels=True)])


@lru_cache(maxsize=None)
def q_impact_inferior_levels() -> Q:
    return join_qs([Q(**{f"role__{right.name}": True})
                    for right in Right.objects.filter(impact_inferior_levels=True)])