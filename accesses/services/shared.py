from __future__ import annotations
from typing import List

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


class RightGroup:
    def __init__(self,
                 name: str,
                 description: str,
                 rights: List[Right],
                 parent: RightGroup = None,
                 child_groups: List[RightGroup] = None):
        self.name = name
        self.description = description
        self.rights = rights
        self.parent = parent
        self.child_groups = child_groups or []

    def __repr__(self):
        return self.name


class RightGroupService:

    def does_role1_prime_over_role2(self, role1, role2) -> bool:
        """
        for role1 to prime over rol2, the True rights on role2 must be True for role1 or higher rights of the same kind are True
        """
        right_groups1 = self.get_right_groups(role1)
        right_groups2 = self.get_right_groups(role2)

        for rg in right_groups2:
            rg_parents = []
            parent = rg.parent
            while parent:
                rg_parents.append(parent)
                parent = parent.parent
            if all(p not in right_groups1 for p in rg_parents):
                return False
        return True

    @staticmethod
    def get_right_groups(role) -> List[RightGroup]:
        right_groups = []

        def get_right_group(rg: RightGroup):
            for right in map(lambda r: r.name, rg.rights):
                if getattr(role, right, False):
                    right_groups.append(rg)
                    break
            return right_groups + sum([get_right_group(c) for c in rg.child_groups], [])

        return right_groups + get_right_group(rg=full_admin_rights)


right_groups_service = RightGroupService()


# ----------------------------------------------    Perimeters hierarchy agnostic rights/global rights
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

# ----------------------------------------------    Perimeters hierarchy dependent rights
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


data_rights = RightGroup(name="data_rights",
                         description="Allow to read patient data",
                         rights=[right_read_patient_nominative,
                                 right_read_patient_pseudonymized,
                                 right_search_patients_by_ipp,
                                 right_search_opposed_patients])
data_accesses_management_rights = RightGroup(name="data_accesses_management_rights",
                                             description="Allow to manage accesses with rights related to reading patients data",
                                             rights=[right_manage_data_accesses_same_level,
                                                     right_read_data_accesses_same_level,
                                                     right_manage_data_accesses_inferior_levels,
                                                     right_read_data_accesses_inferior_levels],
                                             child_groups=[data_rights])
data_rights.parent = data_accesses_management_rights
admin_accesses_management_rights = RightGroup(name="admin_accesses_management_rights",
                                              description="Allow to manage accesses with rights related to data_accesses admins",
                                              rights=[right_manage_admin_accesses_same_level,
                                                      right_read_admin_accesses_same_level,
                                                      right_manage_admin_accesses_inferior_levels,
                                                      right_read_admin_accesses_inferior_levels],
                                              child_groups=[data_accesses_management_rights])
data_accesses_management_rights.parent = admin_accesses_management_rights
jupyter_export_rights = RightGroup(name="jupyter_export_rights",
                                   description="Allow to make Jupyter exports",
                                   rights=[right_export_jupyter_nominative,
                                           right_export_jupyter_pseudonymized])
jupyter_export_accesses_management_rights = RightGroup(name="jupyter_export_accesses_management_rights",
                                                       description="Allow to manage accesses with rights related to making Jupyter exports",
                                                       rights=[right_manage_export_jupyter_accesses],
                                                       child_groups=[jupyter_export_rights])
jupyter_export_rights.parent = jupyter_export_accesses_management_rights
csv_export_rights = RightGroup(name="csv_export_rights",
                               description="Allows to make CSV exports",
                               rights=[right_export_csv_nominative,
                                       right_export_csv_pseudonymized])
csv_export_accesses_management_rights = RightGroup(name="csv_export_accesses_management_rights",
                                                   description="Allow to manage accesses with rights related to making CSV exports",
                                                   rights=[right_manage_export_csv_accesses],
                                                   child_groups=[csv_export_rights])
csv_export_rights.parent = csv_export_accesses_management_rights
users_rights = RightGroup(name="users_rights",
                          description="Allow to manage/read users",
                          rights=[right_manage_users,
                                  right_read_users])
logs_rights = RightGroup(name="logs_rights",
                         description="Allow to read logs",
                         rights=[right_read_logs])
datalabs_rights = RightGroup(name="datalabs_rights",
                             description="Allow to manage/read datalabs",
                             rights=[right_manage_datalabs,
                                     right_read_datalabs])
full_admin_rights = RightGroup(name="full_admin_rights",
                               description="Super user, full admin",
                               rights=[right_full_admin],
                               child_groups=[roles_rights,
                                             users_rights,
                                             logs_rights,
                                             datalabs_rights,
                                             jupyter_export_accesses_management_rights,
                                             csv_export_accesses_management_rights,
                                             admin_accesses_management_rights])
for group in full_admin_rights.child_groups:
    group.parent = full_admin_rights
