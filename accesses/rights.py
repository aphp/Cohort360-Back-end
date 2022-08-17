from __future__ import annotations
from typing import List


class Right:
    def __init__(self, name: str, allow_read_rights_on_same_level: bool = False,
                 allow_read_rights_on_inf_levels: bool = False,
                 allow_read_rights_on_any_level: bool = False,
                 allow_edit_rights_on_same_level: bool = False,
                 allow_edit_rights_on_inf_levels: bool = False,
                 allow_edit_rights_on_any_level: bool = False):
        self.name = name
        self.allow_read_rights_on_same_level = allow_read_rights_on_same_level
        self.allow_read_rights_on_inf_levels = allow_read_rights_on_inf_levels
        self.allow_read_rights_on_any_level = allow_read_rights_on_any_level
        self.allow_edit_rights_on_same_level = allow_edit_rights_on_same_level
        self.allow_edit_rights_on_inf_levels = allow_edit_rights_on_inf_levels
        self.allow_edit_rights_on_any_level = allow_edit_rights_on_any_level

    def __repr__(self):
        return self.name


class RightGroup:
    def __init__(self, name: str, rights: List[Right],
                 parent: RightGroup = None, children: List[RightGroup] = None):
        self.name = name
        self.rights = rights
        self.parent = parent
        self.children = children or []

    def __repr__(self):
        return self.name

    @property
    def rights_read_on_inferior_levels(self) -> List[Right]:
        return [r for r in self.rights if r.allow_read_rights_on_inf_levels]

    @property
    def rights_read_on_same_level(self) -> List[Right]:
        return [r for r in self.rights if r.allow_read_rights_on_same_level]

    @property
    def rights_edit_on_inferior_levels(self) -> List[Right]:
        return [r for r in self.rights if r.allow_edit_rights_on_inf_levels]

    @property
    def rights_edit_on_same_level(self) -> List[Right]:
        return [r for r in self.rights if r.allow_edit_rights_on_same_level]

    @property
    def rights_read_on_any_level(self) -> List[Right]:
        return [r for r in self.rights if r.allow_read_rights_on_any_level]

    @property
    def rights_edit_on_any_level(self) -> List[Right]:
        return [r for r in self.rights if r.allow_edit_rights_on_any_level]

    @property
    def rights_allowing_reading_accesses(self) -> List[Right]:
        return [r for r in self.rights
                if r.allow_read_rights_on_any_level
                or r.allow_read_rights_on_same_level
                or r.allow_read_rights_on_inf_levels]

    @property
    def children_rights(self) -> List[Right]:
        return sum([c.rights + c.children_rights for c in self.children], [])

    @property
    def unreadable_rights(self) -> List[Right]:
        # when you can read accesses that allows themselves to read/manage
        # accesses these accesses will also have right_read_users
        # so you can read it in that case
        can_read_any_admin_accesses = any(len(c.children)
                                          for c in self.children)
        return [r for r in all_rights
                if r not in self.children_rights
                + (self.rights if self.parent is None else [])
                + ([right_read_users] if can_read_any_admin_accesses else [])]


right_read_patient_nominative = Right("right_read_patient_nominative")
right_read_patient_pseudo_anonymised = Right(
    "right_read_patient_pseudo_anonymised")
right_search_patient_with_ipp = Right("right_search_patient_with_ipp")
right_manage_data_accesses_same_level = Right(
    "right_manage_data_accesses_same_level",
    allow_edit_rights_on_same_level=True)
right_read_data_accesses_same_level = Right(
    "right_read_data_accesses_same_level",
    allow_read_rights_on_same_level=True)
right_manage_data_accesses_inferior_levels = Right(
    "right_manage_data_accesses_inferior_levels",
    allow_edit_rights_on_inf_levels=True)
right_read_data_accesses_inferior_levels = Right(
    "right_read_data_accesses_inferior_levels",
    allow_read_rights_on_inf_levels=True)
right_manage_admin_accesses_same_level = Right(
    "right_manage_admin_accesses_same_level",
    allow_edit_rights_on_same_level=True)
right_read_admin_accesses_same_level = Right(
    "right_read_admin_accesses_same_level",
    allow_read_rights_on_same_level=True)
right_manage_admin_accesses_inferior_levels = Right(
    "right_manage_admin_accesses_inferior_levels",
    allow_edit_rights_on_inf_levels=True)
right_read_admin_accesses_inferior_levels = Right(
    "right_read_admin_accesses_inferior_levels",
    allow_read_rights_on_inf_levels=True)
right_review_transfer_jupyter = Right("right_review_transfer_jupyter")
right_manage_review_transfer_jupyter = Right(
    "right_manage_review_transfer_jupyter",
    allow_read_rights_on_any_level=True,
    allow_edit_rights_on_any_level=True)
right_review_export_csv = Right("right_review_export_csv")
right_manage_review_export_csv = Right("right_manage_review_export_csv",
                                       allow_read_rights_on_any_level=True,
                                       allow_edit_rights_on_any_level=True)
right_transfer_jupyter_nominative = Right("right_transfer_jupyter_nominative")
right_transfer_jupyter_pseudo_anonymised = Right(
    "right_transfer_jupyter_pseudo_anonymised")
right_manage_transfer_jupyter = Right("right_manage_transfer_jupyter",
                                      allow_read_rights_on_any_level=True,
                                      allow_edit_rights_on_any_level=True)
right_export_csv_nominative = Right("right_export_csv_nominative")
right_export_csv_pseudo_anonymised = Right("right_export_csv_pseudo_anonymised")
right_manage_export_csv = Right("right_manage_export_csv",
                                allow_read_rights_on_any_level=True,
                                allow_edit_rights_on_any_level=True)
right_read_env_unix_users = Right("right_read_env_unix_users")
right_manage_env_unix_users = Right("right_manage_env_unix_users")
right_manage_env_user_links = Right("right_manage_env_user_links")
right_add_users = Right("right_add_users")
right_edit_users = Right("right_edit_users")
right_read_users = Right("right_read_users")
right_edit_roles = Right("right_edit_roles",
                         allow_read_rights_on_any_level=True,
                         allow_edit_rights_on_any_level=True)
right_read_logs = Right("right_read_logs")

all_rights = [
    right_read_patient_nominative,
    right_read_patient_pseudo_anonymised,
    right_search_patient_with_ipp,
    right_manage_data_accesses_same_level,
    right_read_data_accesses_same_level,
    right_manage_data_accesses_inferior_levels,
    right_read_data_accesses_inferior_levels,
    right_manage_admin_accesses_same_level,
    right_read_admin_accesses_same_level,
    right_manage_admin_accesses_inferior_levels,
    right_read_admin_accesses_inferior_levels,
    right_review_transfer_jupyter,
    right_manage_review_transfer_jupyter,
    right_review_export_csv,
    right_manage_review_export_csv,
    right_transfer_jupyter_nominative,
    right_transfer_jupyter_pseudo_anonymised,
    right_manage_transfer_jupyter,
    right_export_csv_nominative,
    right_export_csv_pseudo_anonymised,
    right_manage_export_csv,
    right_read_env_unix_users,
    right_manage_env_unix_users,
    right_manage_env_user_links,
    right_add_users,
    right_edit_users,
    right_read_users,
    right_edit_roles,
    right_read_logs,
]

data_rights = RightGroup(name="data_rights", rights=[
    right_read_patient_nominative,
    right_read_patient_pseudo_anonymised,
    right_search_patient_with_ipp,
])

data_admin_rights = RightGroup(name="data_admin_rights", rights=[
    right_manage_data_accesses_same_level,
    right_read_data_accesses_same_level,
    right_manage_data_accesses_inferior_levels,
    right_read_data_accesses_inferior_levels,
], children=[data_rights])
data_rights.parent = data_admin_rights

admin_manager_rights = RightGroup(name="admin_manager_rights", rights=[
    right_manage_admin_accesses_same_level,
    right_read_admin_accesses_same_level,
    right_manage_admin_accesses_inferior_levels,
    right_read_admin_accesses_inferior_levels,
], children=[data_admin_rights])
data_admin_rights.parent = admin_manager_rights

jup_review_rights = RightGroup(name="jup_review_rights", rights=[
    right_review_transfer_jupyter,
])

jup_review_manage_rights = RightGroup(name="jup_review_manage_rights", rights=[
    right_manage_review_transfer_jupyter,
], children=[jup_review_rights])
jup_review_rights.parent = jup_review_rights

csv_review_rights = RightGroup(name="csv_review_rights", rights=[
    right_review_export_csv,
])

csv_review_manage_rights = RightGroup(name="csv_review_manage_rights", rights=[
    right_manage_review_export_csv,
], children=[csv_review_rights])
csv_review_rights.parent = csv_review_manage_rights

jup_export_rights = RightGroup(name="jup_export_rights", rights=[
    right_transfer_jupyter_nominative,
    right_transfer_jupyter_pseudo_anonymised,
])

jup_export_manage_rights = RightGroup(name="jup_export_manage_rights", rights=[
    right_manage_transfer_jupyter,
], children=[jup_export_rights])
jup_export_rights.parent = jup_export_manage_rights

csv_export_rights = RightGroup(name="csv_export_rights", rights=[
    right_export_csv_nominative,
    right_export_csv_pseudo_anonymised,
])

csv_export_manage_rights = RightGroup(name="csv_export_manage_rights", rights=[
    right_manage_export_csv,
], children=[csv_export_rights])
csv_export_rights.parent = csv_export_manage_rights

workspaces_rights = RightGroup(name="workspaces_rights", rights=[
    right_read_env_unix_users,
    right_manage_env_unix_users,
    right_manage_env_user_links,
])

user_rights = RightGroup(name="user_rights", rights=[
    right_add_users,
    right_edit_users,
    right_read_users,
])

main_admin_rights = RightGroup(name="main_admin_rights", rights=[
    right_edit_roles,
    right_read_logs,
], children=[user_rights, workspaces_rights, csv_export_manage_rights,
             jup_export_manage_rights, jup_review_manage_rights,
             csv_review_manage_rights, admin_manager_rights],
)

for c_ in main_admin_rights.children:
    c_.parent = main_admin_rights
