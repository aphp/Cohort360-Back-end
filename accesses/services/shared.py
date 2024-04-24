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
