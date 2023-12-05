from __future__ import annotations

from accesses.models import Perimeter


class DataRight:

    def __init__(self, user_id: str, perimeter: Perimeter = None, reading_rights: dict = None):
        reading_rights = reading_rights or {}
        self.user_id = user_id
        self.perimeter = perimeter
        self.right_read_patient_nominative = reading_rights.get("right_read_patient_nominative", False)
        self.right_read_patient_pseudonymized = reading_rights.get("right_read_patient_pseudonymized", False)
        self.right_search_patients_by_ipp = reading_rights.get("right_search_patients_by_ipp", False)
        self.right_search_opposed_patients = reading_rights.get("right_search_opposed_patients", False)
        self.right_export_csv_nominative = reading_rights.get("right_export_csv_nominative", False)
        self.right_export_csv_pseudonymized = reading_rights.get("right_export_csv_pseudonymized", False)
        self.right_export_jupyter_nominative = reading_rights.get("right_export_jupyter_nominative", False)
        self.right_export_jupyter_pseudonymized = reading_rights.get("right_export_jupyter_pseudonymized", False)

    def acquire_extra_data_reading_rights(self, dr: DataRight):
        self.right_read_patient_nominative = self.right_read_patient_nominative or dr.right_read_patient_nominative
        self.right_read_patient_pseudonymized = self.right_read_patient_pseudonymized or dr.right_read_patient_pseudonymized
        self.right_search_patients_by_ipp = self.right_search_patients_by_ipp or dr.right_search_patients_by_ipp
        self.right_search_opposed_patients = self.right_search_opposed_patients or dr.right_search_opposed_patients

    def acquire_extra_global_rights(self, dr: DataRight):
        self.right_export_csv_nominative = self.right_export_csv_nominative or dr.right_export_csv_nominative
        self.right_export_csv_pseudonymized = self.right_export_csv_pseudonymized or dr.right_export_csv_pseudonymized
        self.right_export_jupyter_nominative = self.right_export_jupyter_nominative or dr.right_export_jupyter_nominative
        self.right_export_jupyter_pseudonymized = self.right_export_jupyter_pseudonymized or dr.right_export_jupyter_pseudonymized


class PerimeterReadRight:
    def __init__(self,
                 perimeter: "Perimeter",
                 read_nomi: bool = False,
                 read_pseudo: bool = False,
                 allow_search_by_ipp: bool = False,
                 allow_read_opposed_patient: bool = False):
        self.perimeter = perimeter
        self.right_read_patient_nominative = read_nomi
        self.right_read_patient_pseudonymized = read_pseudo
        self.right_search_patients_by_ipp = allow_search_by_ipp
        self.right_read_opposed_patients_data = allow_read_opposed_patient
        if read_nomi:
            self.read_role = "READ_PATIENT_NOMINATIVE"
        elif read_pseudo:
            self.read_role = "READ_PATIENT_PSEUDO_ANONYMIZE"
        else:
            self.read_role = "NO READ PATIENT RIGHT"


class Right:
    def __init__(self,
                 name: str,
                 allow_read_accesses_on_same_level: bool = False,
                 allow_read_accesses_on_inf_levels: bool = False,
                 allow_edit_accesses_on_same_level: bool = False,
                 allow_edit_accesses_on_inf_levels: bool = False,
                 impact_inferior_levels: bool = False):
        self.name = name
        self.allow_read_accesses_on_same_level = allow_read_accesses_on_same_level
        self.allow_read_accesses_on_inf_levels = allow_read_accesses_on_inf_levels
        self.allow_edit_accesses_on_same_level = allow_edit_accesses_on_same_level
        self.allow_edit_accesses_on_inf_levels = allow_edit_accesses_on_inf_levels
        self.impact_inferior_levels = (impact_inferior_levels
                                       or allow_edit_accesses_on_inf_levels
                                       or allow_read_accesses_on_inf_levels)

    def __repr__(self):
        return self.name


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
