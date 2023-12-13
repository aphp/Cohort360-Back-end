from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from accesses.models import Perimeter


@dataclass
class DataRight:
    user_id: str
    perimeter_id: Optional[int] = None
    right_read_patient_nominative: Optional[bool] = False
    right_read_patient_pseudonymized: Optional[bool] = False
    right_search_patients_by_ipp: Optional[bool] = False
    right_search_opposed_patients: Optional[bool] = False
    right_export_csv_nominative: Optional[bool] = False
    right_export_csv_pseudonymized: Optional[bool] = False
    right_export_jupyter_nominative: Optional[bool] = False
    right_export_jupyter_pseudonymized: Optional[bool] = False

    def acquire_extra_data_reading_rights(self, dr: DataRight):
        self.right_read_patient_nominative = self.right_read_patient_nominative or dr.right_read_patient_nominative
        self.right_read_patient_pseudonymized = self.right_read_patient_pseudonymized or dr.right_read_patient_pseudonymized

    def acquire_extra_global_rights(self, dr: DataRight):
        self.right_search_patients_by_ipp = self.right_search_patients_by_ipp or dr.right_search_patients_by_ipp
        self.right_search_opposed_patients = self.right_search_opposed_patients or dr.right_search_opposed_patients
        self.right_export_csv_nominative = self.right_export_csv_nominative or dr.right_export_csv_nominative
        self.right_export_csv_pseudonymized = self.right_export_csv_pseudonymized or dr.right_export_csv_pseudonymized
        self.right_export_jupyter_nominative = self.right_export_jupyter_nominative or dr.right_export_jupyter_nominative
        self.right_export_jupyter_pseudonymized = self.right_export_jupyter_pseudonymized or dr.right_export_jupyter_pseudonymized


@dataclass
class PerimeterReadRight:
    perimeter: Perimeter
    right_read_patient_nominative: bool
    right_read_patient_pseudonymized: bool
    right_search_patients_by_ipp: bool
    right_read_opposed_patients_data: bool

    def __post_init__(self):
        if self.right_read_patient_nominative:
            self.read_role = "READ_PATIENT_NOMINATIVE"
        elif self.right_read_patient_pseudonymized:
            self.read_role = "READ_PATIENT_PSEUDO_ANONYMIZE"
        else:
            self.read_role = "NO READ PATIENT RIGHT"


@dataclass
class Right:
    name: str
    allow_read_accesses_on_same_level: Optional[bool] = False
    allow_read_accesses_on_inf_levels: Optional[bool] = False
    allow_edit_accesses_on_same_level: Optional[bool] = False
    allow_edit_accesses_on_inf_levels: Optional[bool] = False
    impact_inferior_levels: Optional[bool] = False

    def __post_init__(self):
        self.impact_inferior_levels = (self.impact_inferior_levels
                                       or self.allow_edit_accesses_on_inf_levels
                                       or self.allow_read_accesses_on_inf_levels)


# ----------------------------------------------    Global Rights / Perimeters Hierarchy Independent
right_full_admin = Right("right_full_admin")
right_read_logs = Right("right_read_logs")
right_manage_users = Right("right_manage_users")
right_read_users = Right("right_read_users")
right_manage_datalabs = Right("right_manage_datalabs")
right_read_datalabs = Right("right_read_datalabs")

right_export_csv_nominative = Right("right_export_csv_nominative")
right_export_csv_pseudonymized = Right("right_export_csv_pseudonymized")
right_export_jupyter_nominative = Right("right_export_jupyter_nominative")
right_export_jupyter_pseudonymized = Right("right_export_jupyter_pseudonymized")
right_manage_export_csv_accesses = Right("right_manage_export_csv_accesses")
right_manage_export_jupyter_accesses = Right("right_manage_export_jupyter_accesses")

right_search_patients_by_ipp = Right("right_search_patients_by_ipp")
right_search_opposed_patients = Right("right_search_opposed_patients")

right_read_accesses_above_levels = Right("right_read_accesses_above_levels")

# ----------------------------------------------    Relative Rights / Perimeters Hierarchy Dependent
right_read_patient_nominative = Right("right_read_patient_nominative", impact_inferior_levels=True)
right_read_patient_pseudonymized = Right("right_read_patient_pseudonymized", impact_inferior_levels=True)

right_manage_data_accesses_same_level = Right("right_manage_data_accesses_same_level", allow_edit_accesses_on_same_level=True)
right_read_data_accesses_same_level = Right("right_read_data_accesses_same_level", allow_read_accesses_on_same_level=True)
right_manage_data_accesses_inferior_levels = Right("right_manage_data_accesses_inferior_levels", allow_edit_accesses_on_inf_levels=True)
right_read_data_accesses_inferior_levels = Right("right_read_data_accesses_inferior_levels", allow_read_accesses_on_inf_levels=True)

right_manage_admin_accesses_same_level = Right("right_manage_admin_accesses_same_level", allow_edit_accesses_on_same_level=True)
right_read_admin_accesses_same_level = Right("right_read_admin_accesses_same_level", allow_read_accesses_on_same_level=True)
right_manage_admin_accesses_inferior_levels = Right("right_manage_admin_accesses_inferior_levels", allow_edit_accesses_on_inf_levels=True)
right_read_admin_accesses_inferior_levels = Right("right_read_admin_accesses_inferior_levels", allow_read_accesses_on_inf_levels=True)


all_rights = [right_full_admin,
              right_read_logs,
              right_manage_users,
              right_read_users,
              right_manage_datalabs,
              right_read_datalabs,
              right_export_csv_nominative,
              right_export_csv_pseudonymized,
              right_export_jupyter_nominative,
              right_export_jupyter_pseudonymized,
              right_manage_export_csv_accesses,
              right_manage_export_jupyter_accesses,
              right_read_patient_nominative,
              right_read_patient_pseudonymized,
              right_search_patients_by_ipp,
              right_search_opposed_patients,
              right_manage_data_accesses_same_level,
              right_read_data_accesses_same_level,
              right_manage_data_accesses_inferior_levels,
              right_read_data_accesses_inferior_levels,
              right_manage_admin_accesses_same_level,
              right_read_admin_accesses_same_level,
              right_manage_admin_accesses_inferior_levels,
              right_read_admin_accesses_inferior_levels,
              right_read_accesses_above_levels]
