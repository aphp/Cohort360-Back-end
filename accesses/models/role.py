from __future__ import annotations

from functools import lru_cache

from django.db import models
from django.db.models import Q, UniqueConstraint

from admin_cohort.models import BaseModel


class Role(BaseModel):
    id = models.AutoField(primary_key=True)
    name = models.TextField(blank=True, null=True)
    right_full_admin = models.BooleanField(default=False, null=False)
    right_manage_users = models.BooleanField(default=False, null=False)
    # Datalabs
    right_manage_datalabs = models.BooleanField(default=False, null=False)
    right_read_datalabs = models.BooleanField(default=False, null=False)
    # CSV/Excel exports
    right_export_csv_xlsx_nominative = models.BooleanField(default=False, null=False)
    # Jupyter exports
    right_export_jupyter_nominative = models.BooleanField(default=False, null=False)
    right_export_jupyter_pseudonymized = models.BooleanField(default=False, null=False)
    # Administration accesses management
    right_manage_admin_accesses_same_level = models.BooleanField(default=False, null=False)
    right_manage_admin_accesses_inferior_levels = models.BooleanField(default=False, null=False)
    # Data accesses management
    right_manage_data_accesses_same_level = models.BooleanField(default=False, null=False)
    right_manage_data_accesses_inferior_levels = models.BooleanField(default=False, null=False)
    # Read patient data
    right_read_patient_nominative = models.BooleanField(default=False, null=False)
    right_read_patient_pseudonymized = models.BooleanField(default=False, null=False)
    right_search_patients_by_ipp = models.BooleanField(default=False, null=False)
    right_search_patients_unlimited = models.BooleanField(default=False, null=False)
    right_search_opposed_patients = models.BooleanField(default=False, null=False)


    class Meta:
        constraints = [UniqueConstraint(name="unique_name",
                                        fields=["name"],
                                        condition=Q(delete_datetime__isnull=True))
                       ]

    @lru_cache(maxsize=None)
    def has_any_global_management_right(self):
        return any((self.right_full_admin,
                    self.right_manage_users,
                    self.right_manage_datalabs,))

    @lru_cache(maxsize=None)
    def has_any_global_right(self):
        return any((self.has_any_global_management_right(),
                    self.right_read_datalabs,
                    self.right_search_patients_by_ipp,
                    self.right_search_opposed_patients))

    @lru_cache(maxsize=None)
    def has_any_level_dependent_management_right(self):
        return any((self.right_manage_data_accesses_same_level,
                    self.right_manage_data_accesses_inferior_levels,
                    self.right_manage_admin_accesses_same_level,
                    self.right_manage_admin_accesses_inferior_levels))

    def requires_full_admin_right_to_be_managed(self):
        # requires having: right_full_admin = True
        return self.right_full_admin or \
            self.right_search_patients_unlimited or \
            self.right_manage_admin_accesses_same_level or \
            self.right_manage_admin_accesses_inferior_levels

    def requires_admin_accesses_managing_right_to_be_managed(self):
        # requires having: right_manage_admin_accesses_same/inf_level = True
        return self.right_manage_users or \
            self.right_manage_data_accesses_same_level or \
            self.right_manage_data_accesses_inferior_levels or \
            self.right_manage_datalabs or \
            self.right_read_datalabs

    def requires_data_accesses_managing_right_to_be_managed(self):
        # requires having: right_manage_data_accesses_same/inf_level = True
        return self.right_read_patient_nominative or \
            self.right_read_patient_pseudonymized or \
            self.right_search_patients_by_ipp or \
            self.right_search_opposed_patients or \
            self.right_export_csv_xlsx_nominative or \
            self.right_export_jupyter_nominative or \
            self.right_export_jupyter_pseudonymized
