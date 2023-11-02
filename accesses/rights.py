from __future__ import annotations
from typing import List


class Right:
    def __init__(self,
                 name: str,
                 allow_read_accesses_on_same_level: bool = False,
                 allow_read_accesses_on_inf_levels: bool = False,
                 allow_edit_accesses_on_same_level: bool = False,
                 allow_edit_accesses_on_inf_levels: bool = False,
                 allow_edit_accesses_on_any_level: bool = False,
                 impact_inferior_levels: bool = False):
        self.name = name
        self.allow_read_accesses_on_same_level = allow_read_accesses_on_same_level
        self.allow_read_accesses_on_inf_levels = allow_read_accesses_on_inf_levels
        self.allow_edit_accesses_on_same_level = allow_edit_accesses_on_same_level
        self.allow_edit_accesses_on_inf_levels = allow_edit_accesses_on_inf_levels
        self.allow_edit_accesses_on_any_level = allow_edit_accesses_on_any_level
        self.impact_inferior_levels = (impact_inferior_levels or allow_edit_accesses_on_inf_levels or allow_read_accesses_on_inf_levels)

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

    @property
    def rights_names(self):
        return [right.name for right in self.rights]

    @property
    def rights_read_on_same_level(self) -> List[Right]:
        return [right for right in self.rights if right.allow_read_accesses_on_same_level]

    @property
    def rights_read_on_inferior_levels(self) -> List[Right]:
        return [right for right in self.rights if right.allow_read_accesses_on_inf_levels]

    @property
    def rights_edit_on_same_level(self) -> List[Right]:
        return [right for right in self.rights if right.allow_edit_accesses_on_same_level]

    @property
    def rights_edit_on_inferior_levels(self) -> List[Right]:
        return [right for right in self.rights if right.allow_edit_accesses_on_inf_levels]

    @property
    def rights_allowing_reading_accesses(self) -> List[Right]:
        rights = [right for right in self.rights
                  if right.allow_read_accesses_on_same_level
                  or right.allow_read_accesses_on_inf_levels]
        if right_manage_export_csv_accesses in self.rights:
            rights.append(right_manage_export_csv_accesses)
        if right_manage_export_jupyter_accesses in self.rights:
            rights.append(right_manage_export_jupyter_accesses)
        return rights

    @property
    def child_groups_rights(self) -> List[Right]:
        return sum([child_group.rights + child_group.child_groups_rights for child_group in self.child_groups], [])

    @property
    def unreadable_rights(self) -> List[Right]:     # todo: understand this
        # when you can read accesses that by their turn allow to read/manage
        # accesses, these accesses will also have right_read_users
        # so you can read it in that case
        """
        the rights you can read are the ones coming from:
            - any child/grand_child group of the current RightGroup    .child_groups_rights        OR
            - right_read_user if the current RightGroup has at least one grand child group

        So, the rights you can not read are either:
            - attached to a RightGroup in another branch     OR
            - the rights in the current RightGroup if it is the top RightGroup (has no parent)      OR
            - right_read_user if the current RightGroup has no grand child group
        """
        can_read_any_admin_accesses = any(child_group.child_groups for child_group in self.child_groups)
        return [right for right in all_rights
                if right not in (self.child_groups_rights
                                 + (self.rights if self.parent is None else [])
                                 + ([right_read_users] if can_read_any_admin_accesses else []))]


# ----------------------------------------------    Perimeters hierarchy agnostic rights
right_full_admin = Right("right_full_admin")
right_read_logs = Right("right_read_logs")
right_manage_roles = Right("right_manage_roles")
right_read_roles = Right("right_read_roles")
right_manage_users = Right("right_manage_users")
right_read_users = Right("right_read_users")
right_manage_datalabs = Right("right_manage_datalabs")
right_read_datalabs = Right("right_read_datalabs")

# ----------------------------------------------    Perimeters hierarchy related rights
right_read_patient_nominative = Right("right_read_patient_nominative", impact_inferior_levels=True)
right_read_patient_pseudonymized = Right("right_read_patient_pseudonymized", impact_inferior_levels=True)
right_search_patients_by_ipp = Right("right_search_patients_by_ipp", impact_inferior_levels=True)
right_read_research_opposed_patient_data = Right("right_read_research_opposed_patient_data", impact_inferior_levels=True)
right_manage_data_accesses_same_level = Right("right_manage_data_accesses_same_level", allow_edit_accesses_on_same_level=True)
right_read_data_accesses_same_level = Right("right_read_data_accesses_same_level", allow_read_accesses_on_same_level=True)
right_manage_data_accesses_inferior_levels = Right("right_manage_data_accesses_inferior_levels", allow_edit_accesses_on_inf_levels=True)
right_read_data_accesses_inferior_levels = Right("right_read_data_accesses_inferior_levels", allow_read_accesses_on_inf_levels=True)
right_manage_admin_accesses_same_level = Right("right_manage_admin_accesses_same_level", allow_edit_accesses_on_same_level=True)
right_read_admin_accesses_same_level = Right("right_read_admin_accesses_same_level", allow_read_accesses_on_same_level=True)
right_manage_admin_accesses_inferior_levels = Right("right_manage_admin_accesses_inferior_levels", allow_edit_accesses_on_inf_levels=True)
right_read_admin_accesses_inferior_levels = Right("right_read_admin_accesses_inferior_levels", allow_read_accesses_on_inf_levels=True)
right_read_accesses_above_levels = Right("right_read_accesses_above_levels")    # todo: process this right differently

# ----------------------------------------------    Global rights, hierarchy agnostic rights
right_export_csv_nominative = Right("right_export_csv_nominative")
right_export_csv_pseudonymized = Right("right_export_csv_pseudonymized")
right_export_jupyter_nominative = Right("right_export_jupyter_nominative")
right_export_jupyter_pseudonymized = Right("right_export_jupyter_pseudonymized")

# ----------------------------------------------    Global rights, hierarchy agnostic rights with management capabilities
right_manage_export_csv_accesses = Right("right_manage_export_csv_accesses", allow_edit_accesses_on_any_level=True)
right_manage_export_jupyter_accesses = Right("right_manage_export_jupyter_accesses", allow_edit_accesses_on_any_level=True)

all_rights = [right_full_admin,
              right_read_logs,
              right_manage_roles,
              right_read_roles,
              right_manage_users,
              right_read_users,
              right_manage_datalabs,
              right_read_datalabs,
              right_read_patient_nominative,
              right_read_patient_pseudonymized,
              right_search_patients_by_ipp,
              right_read_research_opposed_patient_data,
              right_manage_data_accesses_same_level,
              right_read_data_accesses_same_level,
              right_manage_data_accesses_inferior_levels,
              right_read_data_accesses_inferior_levels,
              right_manage_admin_accesses_same_level,
              right_read_admin_accesses_same_level,
              right_manage_admin_accesses_inferior_levels,
              right_read_admin_accesses_inferior_levels,
              right_read_accesses_above_levels,
              right_export_csv_nominative,
              right_export_csv_pseudonymized,
              right_export_jupyter_nominative,
              right_export_jupyter_pseudonymized,
              right_manage_export_csv_accesses,
              right_manage_export_jupyter_accesses]

data_rights = RightGroup(name="data_rights",
                         description="Allow to read patient data",
                         rights=[right_read_patient_nominative,
                                 right_read_patient_pseudonymized,
                                 right_search_patients_by_ipp,
                                 right_read_research_opposed_patient_data])

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

roles_rights = RightGroup(name="roles_rights",
                          description="Allow to manage/read roles",
                          rights=[right_manage_roles,
                                  right_read_roles])

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


for c in full_admin_rights.child_groups:
    c.parent = full_admin_rights
