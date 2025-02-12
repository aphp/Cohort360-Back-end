from __future__ import annotations

from functools import lru_cache

from django.db import models
from django.db.models import Q, UniqueConstraint

from admin_cohort.models import BaseModel


class Role(BaseModel):
    id = models.AutoField(primary_key=True)
    name = models.TextField(blank=True, null=True)
    right_full_admin = models.BooleanField(default=False, null=False)
    right_read_logs = models.BooleanField(default=False, null=False)
    right_manage_users = models.BooleanField(default=False, null=False)
    right_read_users = models.BooleanField(default=False, null=False)
    # Datalabs
    right_manage_datalabs = models.BooleanField(default=False, null=False)
    right_read_datalabs = models.BooleanField(default=False, null=False)
    # CSV exports
    right_manage_export_csv_accesses = models.BooleanField(default=False, null=False)
    right_export_csv_nominative = models.BooleanField(default=False, null=False)
    right_export_csv_pseudonymized = models.BooleanField(default=False, null=False)
    # Jupyter exports
    right_manage_export_jupyter_accesses = models.BooleanField(default=False, null=False)
    right_export_jupyter_nominative = models.BooleanField(default=False, null=False)
    right_export_jupyter_pseudonymized = models.BooleanField(default=False, null=False)
    # Administration accesses reading/management
    right_manage_admin_accesses_same_level = models.BooleanField(default=False, null=False)
    right_read_admin_accesses_same_level = models.BooleanField(default=False, null=False)
    right_manage_admin_accesses_inferior_levels = models.BooleanField(default=False, null=False)
    right_read_admin_accesses_inferior_levels = models.BooleanField(default=False, null=False)
    right_read_accesses_above_levels = models.BooleanField(default=False, null=False)
    # Data accesses reading/management
    right_manage_data_accesses_same_level = models.BooleanField(default=False, null=False)
    right_read_data_accesses_same_level = models.BooleanField(default=False, null=False)
    right_manage_data_accesses_inferior_levels = models.BooleanField(default=False, null=False)
    right_read_data_accesses_inferior_levels = models.BooleanField(default=False, null=False)
    # Read patient data
    right_read_patient_nominative = models.BooleanField(default=False, null=False)
    right_read_patient_pseudonymized = models.BooleanField(default=False, null=False)
    right_search_patients_by_ipp = models.BooleanField(default=False, null=False)
    right_search_patients_unlimited = models.BooleanField(default=False, null=False)
    right_search_opposed_patients = models.BooleanField(default=False, null=False)
    # ORBIS
    right_read_administrative_data = models.BooleanField(default=False, null=False)
    right_read_medical_data = models.BooleanField(default=False, null=False)
    right_read_treatments_data = models.BooleanField(default=False, null=False)
    # FHIR
    right_read_practitioner_data = models.BooleanField(default=False, null=False)


    class Meta:
        constraints = [UniqueConstraint(name="unique_name",
                                        fields=["name"],
                                        condition=Q(delete_datetime__isnull=True))
                       ]

    @lru_cache(maxsize=None)
    def has_any_global_management_right(self):
        return any((self.right_full_admin,
                    self.right_manage_users,
                    self.right_manage_datalabs,
                    self.right_manage_export_csv_accesses,
                    self.right_manage_export_jupyter_accesses))

    @lru_cache(maxsize=None)
    def has_any_global_right(self):
        return any((self.has_any_global_management_right(),
                    self.right_read_logs,
                    self.right_read_users,
                    self.right_read_datalabs,
                    self.right_search_patients_by_ipp,
                    self.right_search_opposed_patients,
                    self.right_read_accesses_above_levels))

    @lru_cache(maxsize=None)
    def has_any_level_dependent_management_right(self):
        return any((self.right_manage_data_accesses_same_level,
                    self.right_manage_data_accesses_inferior_levels,
                    self.right_manage_admin_accesses_same_level,
                    self.right_manage_admin_accesses_inferior_levels))

    @lru_cache(maxsize=None)
    def has_any_level_dependent_reading_right(self):
        return any((self.right_read_data_accesses_same_level,
                    self.right_read_data_accesses_inferior_levels,
                    self.right_read_admin_accesses_same_level,
                    self.right_read_admin_accesses_inferior_levels))
