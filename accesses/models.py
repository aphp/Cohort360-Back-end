from __future__ import annotations
from enum import Enum
from functools import reduce
from typing import List, Tuple, Dict, Union

from django.db import models
from django.db.models import CASCADE, Q, SET_NULL
from django.db.models.query import QuerySet
from django.utils import timezone
from django.utils.datetime_safe import datetime

from accesses.rights import RightGroup, main_admin_rights, all_rights
from admin_cohort.models import BaseModel, User
from admin_cohort.settings import MANUAL_SOURCE, \
    PERIMETERS_TYPES
from admin_cohort.tools import join_qs, exclude_qs

ADMIN_ROLE_ID = 0
ADMIN_USERS_ROLE_ID = 1
READ_DATA_PSEUDOANONYMISED_ROLE_ID = 2
READ_DATA_NOMINATIVE_ROLE_ID = 3
KNOWN_ROLES_IDS = [
    ADMIN_ROLE_ID, ADMIN_USERS_ROLE_ID,
    READ_DATA_PSEUDOANONYMISED_ROLE_ID, READ_DATA_NOMINATIVE_ROLE_ID
]

# rights that define a role that can manage the most important accesses
role_main_adm_rights = [
    'right_edit_roles',
]
# rights allows to manage Users and see what they do
role_user_adm_rights = [
    'right_add_users',
    'right_edit_users',
    'right_read_logs',
]
# rights that any kind of "access manager" must have
role_any_mng_rights = [
    'right_read_users',
]
# rights that manage accesses with lowest-level data admins
role_adm_mng_rights = [
    'right_manage_admin_accesses_same_level',
    'right_read_admin_accesses_same_level',
    'right_manage_admin_accesses_inferior_levels',
    'right_read_admin_accesses_inferior_levels',
]
# rights that manage accesses with data rights
role_adm_rights = [
    'right_manage_data_accesses_same_level',
    'right_read_data_accesses_same_level',
    'right_manage_data_accesses_inferior_levels',
    'right_read_data_accesses_inferior_levels',
]
# rights that allows data reading
role_data_rights = [
    'right_read_patient_nominative',
    'right_read_patient_pseudo_anonymised',
    'right_search_patient_with_ipp',
]
# rights that manage accesses allowing to make exports
role_mng_export_rights = [
    "right_manage_transfer_jupyter",
    "right_manage_export_csv",
]
# rights that allow to make exports of type hive
role_jupyter_rights = [
    "right_transfer_jupyter_nominative",
    "right_transfer_jupyter_pseudo_anonymised",
]
# rights that allow to make exports of type csv
role_csv_rights = [
    "right_export_csv_nominative",
    "right_export_csv_pseudo_anonymised",
]
# rights that allow to make exports
role_export_rights = role_jupyter_rights + role_csv_rights
# rights that manage accesses allowing to review exports
role_mng_review_rights = [
    "right_manage_review_transfer_jupyter",
    "right_manage_review_export_csv",
]
# rights that allow to review exports
role_review_rights = [
    "right_review_transfer_jupyter",
    "right_review_export_csv",
]

# rights allows to manage/read workspaces models
role_env_unix_users_rights = [
    "right_read_env_unix_users",
    "right_manage_env_unix_users",
    "right_manage_env_user_links",
]


def Q_role_where_right_is_true(prefix: str, right: str) -> Q:
    return Q(**{f'{prefix}__{right}': True})


def Q_readable_with_admin_mng(role_field: str) -> Q:
    """
    build a neutral query Q that filters objects,
    that has 'role_field' as a field to refer to a Role,
    which the user can read with a right to manage admin accesses
    @param role_field: field name that role has on the model
    that will be filtered
    @type role_field: str
    @return: a neutral query Q that can be given
    as a parameter in objects.filter
    @rtype: Q
    """
    # at least one of these rights should be true
    rights_at_least_one_should_be_true: List[str] = (role_adm_rights
                                                     + role_any_mng_rights)
    # none of these rights should be True
    rights_to_exclude: List[str] = [r for r in Role.all_rights() if r not in
                                    role_adm_rights
                                    + role_any_mng_rights + role_data_rights]
    return join_qs([
        Q_role_where_right_is_true(role_field, right)
        for right in rights_at_least_one_should_be_true
    ]) & exclude_qs([
        Q_role_where_right_is_true(role_field, right)
        for right in rights_to_exclude
    ])


def Q_readable_with_data_admin(role_field: str) -> Q:
    """
    build a neutral query Q that filters objects,
    that has 'role_field' as a field to refer to a Role,
    which the user can read with a right to manage admin accesses
    @param role_field: field name that role has on the model
    that will be filtered
    @type role_field: str
    @return: a neutral query Q that can be given
    as a parameter in objects.filter
    @rtype: Q
    """
    # at least one of these rights should be true
    rights_at_least_one_should_be_true: List[str] = role_data_rights
    # none of these rights should be True
    rights_to_exclude: List[str] = [r for r in Role.all_rights() if r not in
                                    role_data_rights]
    return join_qs([
        Q_role_where_right_is_true(role_field, right)
        for right in rights_at_least_one_should_be_true
    ]) & exclude_qs([
        Q_role_where_right_is_true(role_field, right)
        for right in rights_to_exclude
    ])


def Q_role_on_lower_levels(role_field: str) -> Q:
    """
    build a neutral query Q that filters objects,
    that has 'role_field' as a field to refer to a Role,
    whom the Role has a right on inferior_levels
    It concerns rights that have real effects on perimeters of lower levels
    (right_edit_roles is not bound to any perimeter, but can create some
    accesses to any perimeter)
    @param role_field: field name that role has on the model
    that will be filtered
    @type role_field: str
    @return: a neutral query Q that can be given
    as a parameter in objects.filter
    @rtype: Q
    """
    rights_at_least_one_should_be_true: List[str] = \
        role_main_adm_rights + role_user_adm_rights \
        + list(filter(
            lambda r: '_inferior_' in r,
            role_adm_mng_rights + role_adm_rights
        )) + role_data_rights

    return join_qs([
        Q_role_where_right_is_true(role_field, right)
        for right in rights_at_least_one_should_be_true
    ])


def Q_readable_with_role_admin_access(role_field: str) -> Q:
    """
    build a neutral query Q that filters objects,
    that has 'role_field' as a field to refer to a Role,
    which the user can read with a right to manage admin-managing accesses
    @param role_field: field name that role has on the model
    that will be filtered
    @type role_field: str
    @return: a neutral query Q that can be given
    as a parameter in objects.filter
    @rtype: Q
    """
    rights_at_least_one_should_be_true: List[str] = \
        role_main_adm_rights + role_user_adm_rights + role_any_mng_rights \
        + role_adm_mng_rights + role_mng_export_rights \
        + role_mng_review_rights + role_env_unix_users_rights

    return join_qs([
        Q_role_where_right_is_true(role_field, right)
        for right in rights_at_least_one_should_be_true
    ])


def Q_readable_with_review_jup_mng_access(role_field: str) -> Q:
    """
    build a neutral query Q that filters objects,
    that has 'role_field' as a field to refer to a Role,
    which the user can read with
    a right to manage jupyter transfer reviewing accesses
    @param role_field: field name that role has on the model
    that will be filtered
    @type role_field: str
    @return: a neutral query Q that can be given
    as a parameter in objects.filter
    @rtype: Q
    """
    rights_at_least_one_should_be_true: List[str] = \
        ['right_review_transfer_jupyter']

    rights_to_exclude: List[str] = [r for r in Role.all_rights() if r not in
                                    ["right_review_transfer_jupyter"]]

    return join_qs([
        Q_role_where_right_is_true(role_field, right)
        for right in rights_at_least_one_should_be_true
    ]) & exclude_qs([
        Q_role_where_right_is_true(role_field, right)
        for right in rights_to_exclude
    ])


def Q_readable_with_jupyter_mng_access(role_field: str) -> Q:
    """
    build a neutral query Q that filters objects,
    that has 'role_field' as a field to refer to a Role,
    which the user can read with
    a right to manage jupyter transfer accesses
    @param role_field: field name that role has on the model
    that will be filtered
    @type role_field: str
    @return: a neutral query Q that can be given
    as a parameter in objects.filter
    @rtype: Q
    """
    rights_at_least_one_should_be_true: List[str] = role_jupyter_rights

    rights_to_exclude: List[str] = [r for r in Role.all_rights() if r not in
                                    role_jupyter_rights]

    return join_qs([
        Q_role_where_right_is_true(role_field, right)
        for right in rights_at_least_one_should_be_true
    ]) & exclude_qs([
        Q_role_where_right_is_true(role_field, right)
        for right in rights_to_exclude
    ])


def Q_readable_with_review_csv_mng_access(role_field: str) -> Q:
    """
    build a neutral query Q that filters objects,
    that has 'role_field' as a field to refer to a Role,
    which the user can read with
    a right to manage jupyter transfer accesses
    @param role_field: field name that role has on the model
    that will be filtered
    @type role_field: str
    @return: a neutral query Q that can be given
    as a parameter in objects.filter
    @rtype: Q
    """
    rights_at_least_one_should_be_true: List[str] = \
        ["right_review_export_csv"]

    rights_to_exclude: List[str] = [r for r in Role.all_rights() if r not in
                                    ["right_review_export_csv"]]

    return join_qs([
        Q_role_where_right_is_true(role_field, right)
        for right in rights_at_least_one_should_be_true
    ]) & exclude_qs([
        Q_role_where_right_is_true(role_field, right)
        for right in rights_to_exclude
    ])


def Q_readable_with_csv_mng_access(role_field: str) -> Q:
    """
    build a neutral query Q that filters objects,
    that has 'role_field' as a field to refer to a Role,
    which the user can read with
    a right to manage csv export accesses
    @param role_field: field name that role has on the model
    that will be filtered
    @type role_field: str
    @return: a neutral query Q that can be given
    as a parameter in objects.filter
    @rtype: Q
    """
    rights_at_least_one_should_be_true: List[str] = role_csv_rights

    rights_to_exclude: List[str] = [r for r in Role.all_rights() if r not in
                                    role_csv_rights]

    return join_qs([
        Q_role_where_right_is_true(role_field, right)
        for right in rights_at_least_one_should_be_true
    ]) & exclude_qs([
        Q_role_where_right_is_true(role_field, right)
        for right in rights_to_exclude
    ])


class RoleType(Enum):
    # Matches the roles that have right_edit_role=True
    MAIN_ADMIN: int = 0
    # Matches the roles that have read right on admin rights
    ADMIN_MANAGER_READ: int = 1
    # Matches the roles that have read right on data reading rights
    ADMIN_READ: int = 2
    # Matches the roles that have a data access
    DATA_ACCESS: int = 3
    # Matches the roles that have a manage right on either admin_managers,
    # admins or data_access
    MANAGING_ACCESS: int = 4
    # Matches the roles that have csv export managing right
    MANAGING_CSV_EXPORT: int = 5
    # Matches the roles that have csv export reviewing managing right
    MANAGING_CSV_EXPORT_REVIEW: int = 6
    # Matches the roles that have jupyter transfer managing right
    MANAGING_JUPYTER_TRANSFER: int = 7
    # Matches the roles that have jupyter transfer reviewing managing right
    MANAGING_JUPYTER_TRANSFER_REVIEW: int = 8


def right_field():
    return models.BooleanField(default=False, null=False)


class ReadableRightSet:
    def __init__(self, on_inferior_levels: List[str], on_same_level: List[str],
                 on_all_levels: List[str]):
        self.on_inferior_levels = on_inferior_levels
        self.on_same_level = on_same_level
        self.on_all_levels = on_all_levels


class Role(BaseModel):
    id = models.AutoField(primary_key=True)
    name = models.TextField(blank=True, null=True)
    invalid_reason = models.TextField(blank=True, null=True)

    right_edit_roles = right_field()
    right_read_logs = right_field()

    right_add_users = right_field()
    right_edit_users = right_field()
    right_read_users = right_field()

    right_manage_admin_accesses_same_level = right_field()
    right_read_admin_accesses_same_level = right_field()
    right_manage_admin_accesses_inferior_levels = right_field()
    right_read_admin_accesses_inferior_levels = right_field()

    right_manage_data_accesses_same_level = right_field()
    right_read_data_accesses_same_level = right_field()
    right_manage_data_accesses_inferior_levels = right_field()
    right_read_data_accesses_inferior_levels = right_field()

    right_read_patient_nominative = right_field()
    right_read_patient_pseudo_anonymised = right_field()
    right_search_patient_with_ipp = right_field()

    # JUPYTER TRANSFER
    right_manage_review_transfer_jupyter = right_field()
    right_review_transfer_jupyter = right_field()
    right_manage_transfer_jupyter = right_field()
    right_transfer_jupyter_nominative = right_field()
    right_transfer_jupyter_pseudo_anonymised = right_field()

    # CSV EXPORT
    right_manage_review_export_csv = right_field()
    right_review_export_csv = right_field()
    right_manage_export_csv = right_field()
    right_export_csv_nominative = right_field()
    right_export_csv_pseudo_anonymised = right_field()

    # environments
    right_read_env_unix_users = right_field()
    right_manage_env_unix_users = right_field()
    right_manage_env_user_links = right_field()

    _readable_right_set = None
    _right_groups = None
    _inf_level_read_rights = None
    _same_level_read_rights = None

    @classmethod
    def all_rights(cls):
        return [f.name for f in cls._meta.fields if f.name.startswith("right_")]

    @property
    def right_groups(self) -> List[RightGroup]:
        def get_right_group(rg: RightGroup):
            res = []
            for r in map(lambda x: x.name, rg.rights):
                if getattr(self, r):
                    res.append(rg)
                    break
            return res + sum([get_right_group(c) for c in rg.children], [])

        if self._right_groups is None:
            self._right_groups = get_right_group(main_admin_rights)
        return self._right_groups

    @property
    def inf_level_read_rights(self) -> List[str]:
        """
        Returns rights that, when bound to an access through a Role,
        this role allows a user to read
        on the children of the perimeter of the access this role is bound to
        :return:
        """
        if self._inf_level_read_rights is None:
            res = []
            for rg in self.right_groups:
                for right in rg.rights_read_on_inferior_levels:
                    if getattr(self, right.name):
                        readable_rights = sum([[r.name for r in c.rights]
                                               for c in rg.children], [])
                        if any([len(c.children) for c in rg.children]):
                            readable_rights.append("right_read_users")
                        res.extend(readable_rights)
            self._inf_level_read_rights = list(set(res))
        return self._inf_level_read_rights

        # return list(set(
        #     ([
        #          "right_manage_data_accesses_same_level",
        #          "right_read_data_accesses_same_level",
        #          "right_manage_data_accesses_inferior_levels",
        #          "right_read_data_accesses_inferior_levels",
        #          "right_read_users",
        #      ] if self.right_read_admin_accesses_inferior_levels else [])
        #     + ([
        #            "right_read_patient_nominative",
        #            "right_read_patient_pseudo_anonymised",
        #            "right_search_patient_with_ipp",
        #        ] if self.right_read_admin_accesses_inferior_levels else [])
        # ))

    @property
    def same_level_read_rights(self) -> List[str]:
        """
        Returns rights that, when bound to an access through a Role,
        this role allows a user to read
        on the same perimeter of the access this role is bound to
        :return:
        """
        if self._same_level_read_rights is None:
            res = []
            for rg in self.right_groups:
                for right in rg.rights_read_on_same_level:
                    if getattr(self, right.name):
                        readable_rights = sum([[r.name for r in c.rights]
                                               for c in rg.children], [])
                        if any([len(c.children) for c in rg.children]):
                            readable_rights.append("right_read_users")
                        res.extend(readable_rights)
            self._same_level_read_rights = list(set(res))
        return self._same_level_read_rights

        # return list(set(
        #     ([
        #          "right_manage_data_accesses_same_level",
        #          "right_read_data_accesses_same_level",
        #          "right_manage_data_accesses_inferior_levels",
        #          "right_read_data_accesses_inferior_levels",
        #          "right_read_users",
        #      ] if self.right_read_admin_accesses_same_level else [])
        #     + ([
        #            "right_read_patient_nominative",
        #            "right_read_patient_pseudo_anonymised",
        #            "right_search_patient_with_ipp",
        #        ] if self.right_read_admin_accesses_same_level else [])
        # ))

    @property
    def any_level_read_rights(self) -> List[str]:
        res = []
        for rg in self.right_groups:
            for right in rg.rights_read_on_any_level:
                if getattr(self, right.name):
                    readable_rights = sum([[r.name for r in c.rights]
                                           for c in rg.children], [])
                    if any([len(c.children) for c in rg.children]):
                        readable_rights.append("right_read_users")
                    if rg.parent is None:
                        readable_rights.extend([r.name for r in rg.rights])
                    res.extend(readable_rights)
        return list(set(res))
        # return list(set(
        #     ([
        #          "right_edit_roles",
        #          "right_read_logs",
        #          "right_add_users",
        #          "right_edit_users",
        #          "right_read_users",
        #          "right_manage_admin_accesses_same_level",
        #          "right_read_admin_accesses_same_level",
        #          "right_manage_admin_accesses_inferior_levels",
        #          "right_read_admin_accesses_inferior_levels",
        #          "right_manage_review_transfer_jupyter",
        #          "right_manage_transfer_jupyter",
        #          "right_manage_review_export_csv",
        #          "right_manage_export_csv",
        #          "right_read_env_unix_users",
        #          "right_manage_env_unix_users",
        #          "right_manage_env_user_links",
        #      ] if self.right_edit_roles else [])
        #     + ([
        #            "right_review_transfer_jupyter",
        #        ] if self.right_manage_review_transfer_jupyter else [])
        #     + ([
        #            "right_transfer_jupyter_nominative",
        #            "right_transfer_jupyter_pseudo_anonymised",
        #        ] if self.right_manage_transfer_jupyter else [])
        #     + ([
        #            "right_review_export_csv",
        #        ] if self.right_manage_review_export_csv else [])
        #     + ([
        #            "right_export_csv_nominative",
        #            "right_export_csv_pseudo_anonymised",
        #        ] if self.right_manage_export_csv else [])
        # ))

    @property
    def unreadable_rights(self) -> List[Dict]:
        """
        Returns rights that, when bound to an access through a Role,
        this role allows a user to read
        on the same perimeter of the access this role is bound to
        :return:
        """

        def intersec_criteria(cs_a: List[Dict], cs_b: List[Dict]) -> List[Dict]:
            res = []
            for c_a in cs_a:
                if c_a in cs_b:
                    res.append(c_a)
                else:
                    add = False
                    for c_b in cs_b:
                        if all(c_b.get(r) for r in [k for (k, v) in c_a.items()
                                                    if v]):
                            add = True
                            c_a.update(c_b)
                    if add:
                        res.append(c_a)
            return res

        criteria = list({r.name: True} for r in all_rights)
        for rg in self.right_groups:
            rg_criteria = []
            if any(getattr(self, right.name)
                   for right in rg.rights_allowing_reading_accesses):
                for c in rg.children:
                    if len(c.children_rights):
                        not_true = dict((r.name, False) for r in c.rights)
                        rg_criteria.extend({r.name: True, **not_true}
                                           for r in c.children_rights)
                rg_criteria.extend({r.name: True} for r in rg.unreadable_rights)
                criteria = intersec_criteria(criteria, rg_criteria)

        return criteria

        # if self.right_edit_roles:
        #     qs.append(
        #         join_qs([
        #             Q(**{'right_manage_data_accesses_same_level': True}),
        #             Q(**{'right_read_data_accesses_same_level': True}),
        #             Q(**{'right_manage_data_accesses_inferior_levels': True}),
        #             Q(**{'right_read_data_accesses_inferior_levels': True}),
        #             Q(**{'right_read_patient_nominative': True}),
        #             Q(**{'right_read_patient_pseudo_anonymised': True}),
        #             Q(**{'right_search_patient_with_ipp': True}),
        #         ]) & ~Q(join_qs([
        #             Q(**{'right_manage_admin_accesses_same_level': True}),
        #             Q(**{'right_read_admin_accesses_same_level': True}),
        #             Q(**{'right_manage_admin_accesses_inferior_levels': True}),
        #             Q(**{'right_read_admin_accesses_inferior_levels': True}),
        #         ])))
        #     qs.append(
        #         join_qs([
        #             Q(**{'right_review_transfer_jupyter': True}),
        #         ]) & ~Q(join_qs([
        #             Q(**{'right_manage_review_transfer_jupyter': True}),
        #         ])))
        #     qs.append(
        #         join_qs([
        #             Q(**{'right_transfer_jupyter_nominative': True}),
        #             Q(**{'right_transfer_jupyter_pseudo_anonymised': True}),
        #         ]) & ~Q(join_qs([
        #             Q(**{'right_manage_transfer_jupyter': True}),
        #         ])))
        #     qs.append(
        #         join_qs([
        #             Q(**{'right_review_export_csv': True}),
        #         ]) & ~Q(join_qs([
        #             Q(**{'right_manage_review_export_csv': True}),
        #         ])))
        #     qs.append(
        #         join_qs([
        #             Q(**{'right_export_csv_nominative': True}),
        #             Q(**{'right_export_csv_pseudo_anonymised': True}),
        #         ]) & ~Q(join_qs([
        #             Q(**{'right_manage_export_csv': True}),
        #         ])))
        #
        # if (self.right_read_admin_accesses_same_level
        #         or self.right_read_admin_accesses_inferior_levels):
        #     qs.append(join_qs([
        #         join_qs([
        #             Q(**{'right_read_patient_nominative': True}),
        #             Q(**{'right_read_patient_pseudo_anonymised': True}),
        #             Q(**{'right_search_patient_with_ipp': True}),
        #         ]) & ~Q(join_qs([
        #             Q(**{'right_manage_data_accesses_same_level': True}),
        #             Q(**{'right_read_data_accesses_same_level': True}),
        #             Q(**{'right_manage_data_accesses_inferior_levels': True}),
        #             Q(**{'right_read_data_accesses_inferior_levels': True}),
        #         ]), join_qs([
        #             Q(**{'right_edit_roles': True}),
        #             Q(**{'right_read_logs': True}),
        #             Q(**{'right_add_users': True}),
        #             Q(**{'right_edit_users': True}),
        #             Q(**{'right_manage_review_transfer_jupyter': True}),
        #             Q(**{'right_review_transfer_jupyter': True}),
        #             Q(**{'right_manage_transfer_jupyter': True}),
        #             Q(**{'right_transfer_jupyter_nominative': True}),
        #             Q(**{'right_transfer_jupyter_pseudo_anonymised': True}),
        #             Q(**{'right_manage_review_export_csv': True}),
        #             Q(**{'right_review_export_csv': True}),
        #             Q(**{'right_manage_export_csv': True}),
        #             Q(**{'right_export_csv_nominative': True}),
        #             Q(**{'right_export_csv_pseudo_anonymised': True}),
        #             Q(**{'right_read_env_unix_users': True}),
        #             Q(**{'right_manage_env_unix_users': True}),
        #             Q(**{'right_manage_env_user_links': True}),
        #         ]))
        #     ]))

    @property
    def can_manage_other_accesses(self):
        return self.right_manage_admin_accesses_same_level \
               or self.right_manage_admin_accesses_inferior_levels \
               or self.right_manage_data_accesses_same_level \
               or self.right_manage_data_accesses_inferior_levels \
               or self.right_edit_roles \
               or self.right_manage_review_transfer_jupyter \
               or self.right_manage_transfer_jupyter \
               or self.right_manage_review_export_csv \
               or self.right_manage_export_csv

    @property
    def can_read_other_accesses(self):
        return self.right_edit_roles \
               or self.right_read_admin_accesses_same_level \
               or self.right_read_admin_accesses_inferior_levels \
               or self.right_read_data_accesses_same_level \
               or self.right_read_data_accesses_inferior_levels \
               or self.right_manage_review_transfer_jupyter \
               or self.right_manage_transfer_jupyter \
               or self.right_manage_review_export_csv \
               or self.right_manage_export_csv

    @property
    def requires_manage_review_export_csv_role(self):
        return any([
            self.right_review_export_csv,
        ])

    @property
    def requires_manage_export_csv_role(self):
        return any([
            self.right_export_csv_nominative,
            self.right_export_csv_pseudo_anonymised,
        ])

    @property
    def requires_manage_review_transfer_jupyter_role(self):
        return any([
            self.right_review_transfer_jupyter,
        ])

    @property
    def requires_manage_transfer_jupyter_role(self):
        return any([
            self.right_transfer_jupyter_nominative,
            self.right_transfer_jupyter_pseudo_anonymised,
        ])

    @property
    def requires_admin_role(self):
        return any([
            self.right_read_patient_nominative,
            self.right_search_patient_with_ipp,
            self.right_read_patient_pseudo_anonymised,
        ])

    @property
    def requires_admin_managing_role(self):
        return any([
            self.right_manage_data_accesses_same_level,
            self.right_read_data_accesses_same_level,
            self.right_manage_data_accesses_inferior_levels,
            self.right_read_data_accesses_inferior_levels,
            # self.data_accesses_types
        ])

    @property
    def requires_main_admin_role(self):
        return any([
            self.right_edit_roles,
            self.right_read_logs,
            self.right_add_users,
            self.right_edit_users,
            self.right_manage_admin_accesses_same_level,
            self.right_read_admin_accesses_same_level,
            self.right_manage_admin_accesses_inferior_levels,
            self.right_read_admin_accesses_inferior_levels,
            self.right_read_env_unix_users,
            self.right_manage_env_unix_users,
            self.right_manage_env_user_links,
            self.right_manage_review_transfer_jupyter,
            self.right_manage_transfer_jupyter,
            self.right_manage_review_export_csv,
            self.right_manage_export_csv,
        ])

    @property
    def requires_any_admin_mng_role(self):
        # to be managed, the role requires an access with
        # main admin or admin manager
        return any([
            self.right_read_users,
        ])

    @property
    def help_text(self):
        frs = []

        if self.right_edit_roles:
            frs.append("Gérer les rôles")
        if self.right_read_logs:
            frs.append("Lire l'historique des requêtes des utilisateurs")

        if self.right_add_users:
            frs.append("Ajouter un profil manuel "
                       "pour un utilisateur de l'AP-HP.")
        if self.right_edit_users:
            frs.append("Modifier les profils manuels, "
                       "et activer/désactiver les autres.")
        if self.right_read_users:
            frs.append("Consulter la liste des utilisateurs/profils")

        if self.right_manage_admin_accesses_same_level \
                and self.right_manage_admin_accesses_inferior_levels:
            frs.append("Gérer les accès des administrateurs "
                       "sur son périmètre et ses sous-périmètres")
        else:
            if self.right_manage_admin_accesses_same_level:
                frs.append("Gérer les accès des administrateurs "
                           "sur son périmètre exclusivement")
            if self.right_manage_admin_accesses_inferior_levels:
                frs.append("Gérer les accès des administrateurs "
                           "sur les sous-périmètres exclusivement")

        if self.right_read_admin_accesses_same_level \
                and self.right_read_admin_accesses_inferior_levels:
            frs.append("Consulter la liste des accès administrateurs "
                       "d'un périmètre et ses sous-périmètres")
        else:
            if self.right_read_admin_accesses_same_level:
                frs.append("Consulter la liste des "
                           "accès administrateurs d'un périmètre")
            if self.right_read_admin_accesses_inferior_levels:
                frs.append("Consulter la liste des accès administrateurs "
                           "des sous-périmètres")

        if self.right_manage_data_accesses_same_level \
                and self.right_manage_data_accesses_inferior_levels:
            frs.append("Gérer les accès aux données "
                       "sur son périmètre et ses sous-périmètres")
        else:
            if self.right_manage_data_accesses_same_level:
                frs.append("Gérer les accès aux données "
                           "sur son périmètre exclusivement")
            if self.right_manage_data_accesses_inferior_levels:
                frs.append("Gérer les accès aux données "
                           "sur les sous-périmètres exclusivement")

        if self.right_read_data_accesses_same_level \
                and self.right_read_data_accesses_inferior_levels:
            frs.append("Consulter la liste des accès aux données patients "
                       "d'un périmètre et ses sous-périmètres")
        else:
            if self.right_read_data_accesses_same_level:
                frs.append("Consulter la liste des accès aux "
                           "données patients d'un périmètre")
            if self.right_read_data_accesses_inferior_levels:
                frs.append("Consulter la liste des accès aux données "
                           "patients d'un sous-périmètre")

        if self.right_read_patient_nominative:
            frs.append("Lire les données patient sous forme nominatives "
                       "sur son périmètre et ses sous-périmètres")
        if self.right_search_patient_with_ipp:
            frs.append("Utiliser une liste d'IPP comme "
                       "critère d'une requête Cohort.")
        if self.right_read_patient_pseudo_anonymised:
            frs.append("Lire les données patient sous forme pseudonymisée "
                       "sur son périmètre et ses sous-périmètres")

        # JUPYTER TRANSFER
        if self.right_manage_review_transfer_jupyter:
            frs.append("Gérer les accès permettant de valider "
                       "ou non les demandes de "
                       "transfert de données vers des environnements Jupyter")

        if self.right_review_transfer_jupyter:
            frs.append("Gérer les transferts de données "
                       "vers des environnements Jupyter")

        if self.right_manage_transfer_jupyter:
            frs.append(
                "Gérer les accès permettant de réaliser des demandes de "
                "transfert de données vers des environnements Jupyter")

        if self.right_transfer_jupyter_nominative:
            frs.append("Demander à transférer ses cohortes de patients "
                       "sous forme nominative vers un environnement Jupyter.")
        if self.right_transfer_jupyter_pseudo_anonymised:
            frs.append(
                "Demander à transférer ses cohortes de patients sous "
                "forme pseudonymisée vers un environnement Jupyter.")

        # CSV EXPORT
        if self.right_manage_review_export_csv:
            frs.append("Gérer les accès permettant de valider ou non les "
                       "demandes d'export de données en format CSV")

        if self.right_review_export_csv:
            frs.append("Valider ou non les demandes d'export de données "
                       "en format CSV")

        if self.right_manage_export_csv:
            frs.append(
                "Gérer les accès permettant de réaliser des demandes "
                "d'export de données en format CSV")

        if self.right_export_csv_nominative:
            frs.append("Demander à exporter ses cohortes de patients"
                       " sous forme nominative en format CSV.")

        if self.right_export_csv_pseudo_anonymised:
            frs.append("Demander à exporter ses cohortes de patients sous "
                       "forme pseudonymisée en format CSV.")

        if self.right_read_env_unix_users:
            frs.append(
                "Consulter les informations liées aux environnements "
                "de travail")

        if self.right_manage_env_unix_users:
            frs.append("Gérer les environnements de travail")

        if self.right_manage_env_user_links:
            frs.append(
                "Gérer les accès des utilisateurs aux environnements "
                "de travail")

        return frs

    # @property
    # def readable_right_set(self) -> ReadableRightSet:
    #     if self._readable_right_set is None:
    #         inf, same, all = [dict(), dict(), dict()]
    #         if
    #             self._readable_right_set = ReadableRightSet(
    #                 on_inferior_levels=,
    #                 on_same_level=,
    #                 on_all_levels=,
    #             )
    #     return self._readable_right_set
    #
    # class Meta:
    #     managed = True


def get_specific_roles(role_type=int) \
        -> Tuple[List[models.Model], List[models.Model]]:
    # tested
    """
    Among all the roles in the database, returns those matching the role_type
    (role_type follows Enum RoleType)
    @param role_type:
    @type role_type: member of RoleTYpe enum
    @return: a tuple with a list of matching roles with the rights focusing the
    the same level of care site,
    and the ones wi th the rights focusing on inferior levels of care sites
    @rtype: Tuple[List[Role], List[Role]]
    """
    all_roles = Role.objects.all()
    if role_type == RoleType.DATA_ACCESS:
        roles = [
            r.id for r in
            all_roles.filter(right_read_patient_nominative=True)
            | all_roles.filter(right_read_patient_pseudo_anonymised=True)
            | all_roles.filter(right_search_patient_with_ipp=True)
        ]
        return roles, roles
    elif role_type == RoleType.ADMIN_READ:
        return [r.id for r in all_roles.filter(
            right_read_data_accesses_inferior_levels=True)], \
               [r.id for r in
                all_roles.filter(right_read_data_accesses_same_level=True)]
    elif role_type == RoleType.ADMIN_MANAGER_READ:
        return [r.id for r in all_roles.filter(
            right_read_admin_accesses_inferior_levels=True)], \
               [r.id for r in
                all_roles.filter(right_read_admin_accesses_same_level=True)]
    elif role_type == RoleType.MAIN_ADMIN:
        roles = [r.id for r in all_roles.filter(right_edit_roles=True)]
        return roles, roles
    elif role_type == RoleType.MANAGING_ACCESS:
        return [r.id for r in
                all_roles.filter(
                    right_manage_admin_accesses_inferior_levels=True)
                | all_roles.filter(right_edit_roles=True)
                | all_roles.filter(
                    right_manage_data_accesses_inferior_levels=True)
                | all_roles.filter(right_manage_review_export_csv=True)
                | all_roles.filter(right_manage_export_csv=True)
                | all_roles.filter(
                    right_manage_review_transfer_jupyter=True)
                | all_roles.filter(right_manage_transfer_jupyter=True)
                ], \
               [r.id for r in
                all_roles.filter(
                    right_manage_admin_accesses_same_level=True)
                | all_roles.filter(right_edit_roles=True)
                | all_roles.filter(
                    right_manage_data_accesses_same_level=True)
                | all_roles.filter(right_manage_review_export_csv=True)
                | all_roles.filter(right_manage_export_csv=True)
                | all_roles.filter(
                    right_manage_review_transfer_jupyter=True)
                | all_roles.filter(right_manage_transfer_jupyter=True)
                ]
    elif role_type == RoleType.MANAGING_CSV_EXPORT:
        roles = [r.id for r in all_roles.filter(
            right_manage_review_export_csv=True
        )]
        return roles, roles
    elif role_type == RoleType.MANAGING_CSV_EXPORT_REVIEW:
        roles = [r.id for r in all_roles.filter(
            right_manage_export_csv=True
        )]
        return roles, roles
    elif role_type == RoleType.MANAGING_JUPYTER_TRANSFER:
        roles = [r.id for r in all_roles.filter(
            right_manage_review_transfer_jupyter=True
        )]
        return roles, roles
    elif role_type == RoleType.MANAGING_JUPYTER_TRANSFER_REVIEW:
        roles = [r.id for r in all_roles.filter(
            right_manage_transfer_jupyter=True
        )]
        return roles, roles
    else:
        return [], []


class Profile(BaseModel):
    id = models.AutoField(blank=True, null=False, primary_key=True)
    provider_id = models.BigIntegerField(blank=True, null=True)
    provider_name = models.TextField(blank=True, null=True)
    firstname = models.TextField(blank=True, null=True)
    lastname = models.TextField(blank=True, null=True)
    email = models.TextField(blank=True, null=True)
    source = models.TextField(blank=True, null=True, default=MANUAL_SOURCE)

    is_active = models.BooleanField(blank=True, null=True)
    manual_is_active = models.BooleanField(blank=True, null=True)
    valid_start_datetime: datetime = models.DateTimeField(blank=True,
                                                          null=True)
    manual_valid_start_datetime: datetime = models.DateTimeField(
        blank=True, null=True)
    valid_end_datetime: datetime = models.DateTimeField(blank=True,
                                                        null=True)
    manual_valid_end_datetime: datetime = models.DateTimeField(
        blank=True, null=True)

    user = models.ForeignKey(User, on_delete=CASCADE,
                             related_name='profiles',
                             null=True, blank=True)

    class Meta:
        managed = True

    @property
    def is_valid(self):
        now = datetime.now().replace(tzinfo=None)
        if self.actual_valid_start_datetime is not None:
            if self.actual_valid_start_datetime.replace(tzinfo=None) > now:
                return False
        if self.actual_valid_end_datetime is not None:
            if self.actual_valid_end_datetime.replace(tzinfo=None) <= now:
                return False
        return self.actual_is_active

    @property
    def actual_is_active(self):
        return self.is_active if self.manual_is_active is None \
            else self.manual_is_active

    @property
    def actual_valid_start_datetime(self) -> datetime:
        return self.valid_start_datetime \
            if self.manual_valid_start_datetime is None \
            else self.manual_valid_start_datetime

    @property
    def actual_valid_end_datetime(self) -> datetime:
        return self.valid_end_datetime \
            if self.manual_valid_end_datetime is None \
            else self.manual_valid_end_datetime

    @property
    def cdm_source(self) -> str:
        return str(self.source)

    @classmethod
    def Q_is_valid(cls, field_prefix: str = '') -> Q:
        # now = datetime.now().replace(tzinfo=None)
        now = timezone.now()
        fields = dict(
            valid_start=f"{field_prefix}valid_start_datetime",
            manual_valid_start=f"{field_prefix}manual_valid_start_datetime",
            valid_end=f"{field_prefix}valid_end_datetime",
            manual_valid_end=f"{field_prefix}manual_valid_end_datetime",
            active=f"{field_prefix}is_active",
            manual_active=f"{field_prefix}manual_is_active",
        )
        q_actual_start_is_none = Q(**{
            fields['valid_start']: None,
            fields['manual_valid_start']: None
        })
        q_start_lte_now = ((Q(**{fields['manual_valid_start']: None})
                            & Q(**{f"{fields['valid_start']}__lte": now}))
                           | Q(
                    **{f"{fields['manual_valid_start']}__lte": now}))

        q_actual_end_is_none = Q(**{
            fields['valid_end']: None,
            fields['manual_valid_end']: None
        })
        q_end_gte_now = ((Q(**{fields['manual_valid_end']: None})
                          & Q(**{f"{fields['valid_end']}__gte": now}))
                         | Q(**{f"{fields['manual_valid_end']}__gte": now}))

        q_is_active = ((Q(**{fields['manual_active']: None})
                        & Q(**{fields['active']: True}))
                       | Q(**{fields['manual_active']: True}))
        return ((q_actual_start_is_none | q_start_lte_now)
                & (q_actual_end_is_none | q_end_gte_now)
                & q_is_active)


def get_all_readable_accesses_perimeters(
        accesses: QuerySet, role_type: int
) -> List[str]:
    """
    Will check the provider's accesses
    Will list the roles that allow to read accesses with the role_type required
    Will then pick the provider's accesses that match these roles
    Will finally get the care_sites from these accesses and gather the children
    care_sites when required

    @param accesses:
    @param role_type:
    @param filtered_perim_ids:
    @return:
    """
    roles_with_read_ids_inf_perims, roles_with_read_ids_same_perim = \
        get_specific_roles(role_type)

    same_lvl_perims_ids = [
        str(a.perimeter_id) for a in accesses
        if a.role_id in roles_with_read_ids_same_perim
    ]

    perims_with_inf_perim_role = [
        a.perimeter_id for a in accesses
        if a.role_id in roles_with_read_ids_inf_perims]

    perims_ids = (same_lvl_perims_ids
                  + list(get_all_level_children(perims_with_inf_perim_role,
                                                strict=True,
                                                ids_only=True)))

    return perims_ids


class Perimeter(BaseModel):
    id = models.BigAutoField(primary_key=True)
    local_id = models.CharField(max_length=63, unique=True)
    name = models.TextField(blank=True, null=True)
    source_value = models.TextField(blank=True, null=True)
    short_name = models.TextField(blank=True, null=True)
    type_source_value = models.TextField(blank=True, null=True)
    parent = models.ForeignKey("accesses.perimeter",
                               on_delete=models.CASCADE,
                               related_name="children", null=True)

    @property
    def names(self):
        return dict(name=self.name, short=self.short_name,
                    source_value=self.source_value)

    @property
    def type(self):
        return self.type_source_value

    @property
    def all_children_queryset(self):
        return join_qs([Perimeter.objects.filter(
            **{i * 'parent__' + 'id': self.id}
        ) for i in range(1, len(PERIMETERS_TYPES))])

    class Meta:
        managed = True


def get_all_level_parents_perimeters(
        perimeter_ids: List[int], strict: bool = False,
        ids_only: bool = False
) -> List[Perimeter]:
    q = join_qs([
        Perimeter.objects.filter(
            **{i * 'children__' + 'id__in': perimeter_ids}
        ) for i in range(0 + strict, len(PERIMETERS_TYPES))
    ]).distinct()
    return [str(i[0]) for i in q.values_list('id')] if ids_only else q


def get_all_level_children(
        perimeters_ids: Union[int, List[int]], strict: bool = False,
        filtered_ids: List[str] = [], ids_only: bool = False
) -> List[Union[Perimeter, str]]:
    qs = reduce(
        lambda a, b: a | b,
        [Perimeter.objects.filter(
            **{i * 'parent__' + 'id__in': perimeters_ids}
        ) for i in range(0 + strict,
                         len(PERIMETERS_TYPES))]
    )
    if len(filtered_ids):
        return qs.filter(id__in=filtered_ids)

    if ids_only:
        return [str(i[0]) for i in qs.values_list('id')]
    return list(qs)


class Access(BaseModel):
    id = models.BigAutoField(primary_key=True)
    perimeter = models.ForeignKey(
        Perimeter, to_field='id', on_delete=SET_NULL,
        related_name='accesses', null=True)
    source = models.TextField(blank=True, null=True, default=MANUAL_SOURCE)

    start_datetime = models.DateTimeField(blank=True, null=True)
    end_datetime = models.DateTimeField(blank=True, null=True)
    manual_start_datetime = models.DateTimeField(blank=True, null=True)
    manual_end_datetime = models.DateTimeField(blank=True, null=True)

    profile = models.ForeignKey(Profile, on_delete=CASCADE,
                                related_name='accesses', null=True)
    role: Role = models.ForeignKey(Role, on_delete=CASCADE,
                                   related_name='accesses', null=True)

    @property
    def is_valid(self):
        today = datetime.now()
        if self.actual_start_datetime is not None:
            actual_start_datetime = datetime.combine(
                self.actual_start_datetime.date()
                if isinstance(self.actual_start_datetime, datetime) else
                self.actual_start_datetime,
                datetime.min
            )
            if actual_start_datetime > today:
                return False
        if self.actual_end_datetime is not None:
            actual_end_datetime = datetime.combine(
                self.actual_end_datetime.date()
                if isinstance(self.actual_end_datetime, datetime)
                else self.actual_end_datetime,
                datetime.min
            )
            if actual_end_datetime <= today:
                return False
        return True

    @classmethod
    def Q_is_valid(cls) -> Q:
        # now = datetime.now().replace(tzinfo=None)
        now = timezone.now()
        q_actual_start_is_none = Q(start_datetime=None,
                                   manual_start_datetime=None)
        q_start_lte_now = ((Q(manual_start_datetime=None)
                            & Q(start_datetime__lte=now))
                           | Q(manual_start_datetime__lte=now))

        q_actual_end_is_none = Q(end_datetime=None,
                                 manual_end_datetime=None)
        q_end_gte_now = ((Q(manual_end_datetime=None)
                          & Q(end_datetime__gte=now))
                         | Q(manual_end_datetime__gte=now))
        return ((q_actual_start_is_none | q_start_lte_now)
                & (q_actual_end_is_none | q_end_gte_now))

    # @property
    # def provider_history(self):
    #     return Profile.objects.get(
    #         provider_history_id=self.provider_history_id)

    # @property
    # def perimeter(self):
    #     return Perimeter.objects.get(care_site_id=self.care_site_id)

    @property
    def care_site_id(self):
        return self.perimeter.id

    @property
    def care_site(self):
        return {
            'care_site_id': self.perimeter.id,
            'care_site_name': self.perimeter.name,
            'care_site_short_name': self.perimeter.short_name,
            'care_site_type_source_value': self.perimeter.type_source_value,
            'care_site_source_value': self.perimeter.source_value,
        } if self.perimeter else None

    # @property
    # def role(self):
    #     return Role.objects.get(role_id=self.role_id)

    @property
    def actual_start_datetime(self):
        return self.start_datetime if self.manual_start_datetime is None \
            else self.manual_start_datetime

    @property
    def actual_end_datetime(self):
        return self.end_datetime if self.manual_end_datetime is None \
            else self.manual_end_datetime

    @property
    def include_accesses_to_read_Q(self) -> Q:
        qs = []
        if len(self.role.inf_level_read_rights):
            qs.append(
                join_qs([
                    Q(**{'perimeter__' + i * 'parent__' + 'id': (
                        self.perimeter_id
                    )}) for i in range(1, len(PERIMETERS_TYPES))
                ]) & join_qs([Q(**{f'role__{read_r}': True})
                              for read_r in self.role.inf_level_read_rights])
            )

        if len(self.role.same_level_read_rights):
            qs.append(
                Q(perimeter_id=self.perimeter_id)
                & join_qs([Q(**{f'role__{read_r}': True})
                           for read_r in self.role.same_level_read_rights])
            )

        if len(self.role.any_level_read_rights):
            qs.extend([Q(**{f'role__{read_r}': True})
                       for read_r in self.role.any_level_read_rights])

        return join_qs(qs) if len(qs) else ~Q()

    @property
    def accesses_criteria_to_exclude(self) -> List[Dict]:
        res = self.role.unreadable_rights

        for read_r in (self.role.inf_level_read_rights
                       + self.role.same_level_read_rights):
            d = {read_r: True}

            if read_r in self.role.inf_level_read_rights:
                d['perimeter_not_child'] = [self.perimeter_id]

            if read_r in self.role.same_level_read_rights:
                d['perimeter_not'] = [self.perimeter_id]

            res.append(d)

        return res

    class Meta:
        managed = True


def can_roles_manage_access(
        user_accesses: List[Tuple[Access, Role]], access_role: Role,
        perimeter_id: int, just_read: bool = False
) -> bool:
    """
    Given accesses from a user (perimeter + role), will determine if the user
    has specific rights to manage or read on other accesses,
    either on the perimeter or ones from inferior levels
    Then, depending on what the role requires to be managed,
    or read if just_read=True, will return if the accesses are sufficient
    @param user_accesses:
    @param access_role:
    @param perimeter_id:
    @param can_read: True if we should check the possibility to read, instea of
    to manage
    @return:
    """
    # tested but not with just_read
    has_main_admin_role = any(
        [r.right_edit_roles for [_, r] in user_accesses])

    has_admin_managing_role = any(
        [
            (
                    (
                            (
                                role.right_read_admin_accesses_same_level
                                if just_read
                                else role.right_manage_admin_accesses_same_level
                            ) and str(access_.perimeter_id) == str(perimeter_id)
                    ) or (
                            (
                                role.right_read_admin_accesses_inferior_levels
                                if just_read else
                                role.right_manage_admin_accesses_inferior_levels
                            ) and str(access_.perimeter_id) != str(perimeter_id)
                    )
            ) for [access_, role] in user_accesses
        ]
    )

    has_admin_role = any(
        [
            (
                    (
                            (
                                role.right_read_data_accesses_same_level
                                if just_read
                                else role.right_manage_data_accesses_same_level
                            ) and str(access_.perimeter_id) == str(perimeter_id)
                    ) or (
                            (
                                role.right_read_data_accesses_inferior_levels
                                if just_read else
                                role.right_manage_data_accesses_inferior_levels
                            ) and str(access_.perimeter_id) != str(perimeter_id)
                    )
            ) for [access_, role] in user_accesses
        ]
    )

    has_jupy_rvw_mng_role = any([
        r.right_manage_review_transfer_jupyter for [_, r] in user_accesses
    ])
    has_jupy_mng_role = any([
        r.right_manage_transfer_jupyter for [_, r] in user_accesses
    ])
    has_csv_rvw_mng_role = any([
        r.right_manage_review_export_csv for [_, r] in user_accesses
    ])
    has_csv_mng_role = any([
        r.right_manage_export_csv for [_, r] in user_accesses
    ])

    return (
                   not access_role.requires_main_admin_role
                   or has_main_admin_role
           ) and (
                   not access_role.requires_admin_managing_role
                   or has_admin_managing_role
           ) and (
                   not access_role.requires_admin_role
                   or has_admin_role
           ) and (
                   not access_role.requires_any_admin_mng_role
                   or has_main_admin_role or has_admin_managing_role
           ) and (
                   not access_role.requires_manage_review_transfer_jupyter_role
                   or has_jupy_rvw_mng_role
           ) and (
                   not access_role.requires_manage_transfer_jupyter_role
                   or has_jupy_mng_role
           ) and (
                   not access_role.requires_manage_review_export_csv_role
                   or has_csv_rvw_mng_role
           ) and (
                   not access_role.requires_manage_export_csv_role
                   or has_csv_mng_role
           )


def get_assignable_roles_on_perimeter(
        user: User, perimeter_id: int
) -> List[Role]:
    # tested
    user_accesses = get_all_user_accesses_with_roles_on_perimeter(user,
                                                                  perimeter_id)
    return [
        r for r in Role.objects.all()
        if can_roles_manage_access(user_accesses, r, perimeter_id)
    ]


# more than getting the access on one Perimeter
# will also get the ones from the other perimeters that contain this perimeter
# Perimeters are organised like a tree, perimeters contain other perimeters,
# and roles are thus inherited
def get_all_user_accesses_with_roles_on_perimeter(
        user: User, perimeter_id: int
) -> List[Tuple[Access, Role]]:
    parent_perimeters_ids = get_all_level_parents_perimeters(
        [str(perimeter_id)], ids_only=True)

    q = get_user_valid_manual_accesses_queryset(user)
    accesses = q.filter(
        perimeter_id__in=[p_id for p_id in parent_perimeters_ids],
    ) | q.filter(join_qs([
        Q(role__right_edit_roles=True),
        Q(role__right_add_users=True),
        Q(role__right_edit_users=True),
        Q(role__right_manage_review_transfer_jupyter=True),
        Q(role__right_manage_transfer_jupyter=True),
        Q(role__right_manage_review_export_csv=True),
        Q(role__right_manage_export_csv=True),
    ]))

    return [(access, Role.objects.filter(id=access.role_id).first())
            for access in accesses]


def get_user_valid_manual_accesses_queryset(u: User) -> QuerySet:
    return Access.objects.filter(
        Profile.Q_is_valid(field_prefix="profile__")
        & Q(profile__source=MANUAL_SOURCE)
        & Access.Q_is_valid()
        & Q(profile__user=u)
    )


def get_user_data_accesses_queryset(u: User) -> QuerySet:
    return get_user_valid_manual_accesses_queryset(u).filter(
        join_qs(
            [Q(role__right_read_patient_nominative=True),
             Q(role__right_read_patient_pseudo_anonymised=True),
             Q(role__right_search_patient_with_ipp=True),
             Q(role__right_export_csv_nominative=True),
             Q(role__right_export_csv_pseudo_anonymised=True),
             Q(role__right_transfer_jupyter_pseudo_anonymised=True),
             Q(role__right_transfer_jupyter_nominative=True)]
        )).prefetch_related('role')


def get_user_dict_data_accesses(u: User) -> Dict[int, Access]:
    return dict([(a.id, a) for a in get_user_data_accesses_queryset(u)])


class DataRight:
    def __init__(self, perimeter_id: int, user_id: str, provider_id: int,
                 acc_ids: List[int] = None,
                 pseudo: bool = False, nomi: bool = False,
                 exp_pseudo: bool = False, exp_nomi: bool = False,
                 jupy_pseudo: bool = False, jupy_nomi: bool = False,
                 search_ipp: bool = False, **kwargs) -> Dict:
        """
        @return: a default DataRight as required by the serializer
        """
        if 'perimeter' in kwargs:
            self.perimeter: Perimeter = kwargs['perimeter']
        self.perimeter_id = perimeter_id
        self.provider_id = provider_id
        self.user_id = user_id
        self.access_ids = acc_ids or []
        self.right_read_patient_nominative = nomi
        self.right_read_patient_pseudo_anonymised = pseudo
        self.right_search_patient_with_ipp = search_ipp
        self.right_export_csv_nominative = exp_nomi
        self.right_export_csv_pseudo_anonymised = exp_pseudo
        self.right_transfer_jupyter_nominative = jupy_nomi
        self.right_transfer_jupyter_pseudo_anonymised = jupy_pseudo

    @property
    def rights_granted(self) -> List[str]:
        return [r for r in [
            'right_read_patient_nominative',
            'right_read_patient_pseudo_anonymised',
            'right_search_patient_with_ipp',
        ] if getattr(self, r)]

    @property
    def count_rights_granted(self) -> int:
        return len(self.rights_granted)

    def add_right(self, right: DataRight):
        """
        Adds a new DataRight access id to self access_ids
        and grants new rights given by this new DataRight
        :param right: other DataRight to complete with
        :return:
        """
        self.access_ids = list(set(
            self.access_ids + right.access_ids))
        self.right_read_patient_nominative = \
            self.right_read_patient_nominative \
            or right.right_read_patient_nominative
        self.right_read_patient_pseudo_anonymised = \
            self.right_read_patient_pseudo_anonymised \
            or right.right_read_patient_pseudo_anonymised
        self.right_search_patient_with_ipp = \
            self.right_search_patient_with_ipp \
            or right.right_search_patient_with_ipp

    def add_global_right(self, right: DataRight):
        """
        Adds a new DataRight access id to self access_ids
        and grants new rights given by this new DataRight
        :param right: other DataRight to complete with
        :return:
        """
        self.access_ids = list(set(
            self.access_ids + right.access_ids))
        self.right_export_csv_nominative = \
            self.right_export_csv_nominative \
            or right.right_export_csv_nominative
        self.right_export_csv_pseudo_anonymised = \
            self.right_export_csv_pseudo_anonymised \
            or right.right_export_csv_pseudo_anonymised
        self.right_transfer_jupyter_nominative = \
            self.right_transfer_jupyter_nominative \
            or right.right_transfer_jupyter_nominative
        self.right_transfer_jupyter_pseudo_anonymised = \
            self.right_transfer_jupyter_pseudo_anonymised \
            or right.right_transfer_jupyter_pseudo_anonymised

    def add_access_ids(self, ids: List[int]):
        self.access_ids = list(set(self.access_ids + ids))

    @property
    def has_data_read_right(self):
        return self.right_read_patient_nominative \
               or self.right_read_patient_pseudo_anonymised \
               or self.right_search_patient_with_ipp

    @property
    def has_global_data_right(self):
        return self.right_export_csv_nominative \
               or self.right_export_csv_pseudo_anonymised \
               or self.right_transfer_jupyter_nominative \
               or self.right_transfer_jupyter_pseudo_anonymised

    @property
    def care_site_history_ids(self) -> List[int]:
        return self.access_ids

    @property
    def care_site_id(self) -> int:
        return int(self.perimeter_id)
