from __future__ import annotations

from typing import List, Dict

from django.db.models import Q, F
from django.db.models.query import QuerySet, Prefetch

from accesses.models import Profile, Access, Role, Perimeter
from accesses.rights import all_rights
from admin_cohort.models import User
from admin_cohort.settings import MANUAL_SOURCE, PERIMETERS_TYPES
from admin_cohort.tools import join_qs


def get_role_unreadable_rights(role: Role) -> List[Dict]:  # todo: understand this
    criteria = [{right.name: True} for right in all_rights]
    for rg in role.right_groups:
        rg_criteria = []
        if any(getattr(role, right.name, False) for right in rg.rights_allowing_reading_accesses):
            for child_group in rg.child_groups:
                if child_group.child_groups_rights:
                    not_true = dict((right.name, False) for right in child_group.rights)
                    rg_criteria.extend({right.name: True, **not_true} for right in child_group.child_groups_rights)
            rg_criteria.extend({right.name: True} for right in rg.unreadable_rights)
            criteria = intersect_queryset_criteria(criteria, rg_criteria)
    return criteria


def access_criteria_to_exclude(access: Access) -> List[Dict]:  # todo: understand this
    role = access.role
    unreadable_rights = get_role_unreadable_rights(role=role)

    for right in (role.rights_allowing_to_read_accesses_on_same_level +
                  role.rights_allowing_to_read_accesses_on_inferior_levels):
        d = {right: True}
        if right in role.rights_allowing_to_read_accesses_on_same_level:
            d['perimeter_not'] = [access.perimeter_id]
        if right in role.rights_allowing_to_read_accesses_on_inferior_levels:
            d['perimeter_not_child'] = [access.perimeter_id]
        unreadable_rights.append(d)
    return unreadable_rights


def intersect_queryset_criteria(cs_a: List[Dict], cs_b: List[Dict]) -> List[Dict]:     # todo: understand this
    """
    Given two lists of Role Queryset criteria
    We keep only items that are in both lists
    Item is in both lists if it has the same
    'True' factors (ex.: right_manage_roles=True)
    If an item is in both, we merge the two versions :
    - with keeping 'False' factors,
    - with extending 'perimeter_not' and 'perimeter_not_child' lists
    :param cs_a:
    :param cs_b:
    :return:
    """
    #   [
    #   {'right_manage_data_accesses_same_level': True, 'perimeter_not_child': [8312002244], 'perimeter_not': [8312002244]},
    #   {'right_read_patient_pseudo_anonymised': True, 'perimeter_not_child': [8312002244], 'perimeter_not': [8312002244]},
    #   {'right_search_patient_with_ipp': True, 'perimeter_not_child': [8312002244], 'perimeter_not': [8312002244]},
    #   {'right_read_patient_nominative': True, 'perimeter_not_child': [8312002244], 'perimeter_not': [8312002244]},
    #   {'right_read_data_accesses_inferior_levels': True, 'perimeter_not_child': [8312002244], 'perimeter_not': [8312002244]},
    #   {'right_read_data_accesses_same_level': True, 'perimeter_not_child': [8312002244], 'perimeter_not': [8312002244]},
    #   {'right_manage_data_accesses_inferior_levels': True, 'perimeter_not_child': [8312002244], 'perimeter_not': [8312002244]},
    #   {'right_read_users': True, 'perimeter_not_child': [8312002244], 'perimeter_not': [8312002244]}
    #   ],
    #
    #  [{'right_read_patient_nominative': True}, {'right_read_patient_pseudo_anonymised': True}, {'right_search_patient_with_ipp': True},
    #   {'right_manage_data_accesses_same_level': True}, {'right_read_data_accesses_same_level': True},
    #   {'right_manage_data_accesses_inferior_levels': True}, {'right_read_data_accesses_inferior_levels': True},
    #   {'right_manage_admin_accesses_same_level': True}, {'right_read_admin_accesses_same_level': True},
    #   {'right_manage_admin_accesses_inferior_levels': True}, {'right_read_admin_accesses_inferior_levels': True},
    #   {'right_review_transfer_jupyter': True}, {'right_manage_review_transfer_jupyter': True}, {'right_review_export_csv': True},
    #   {'right_manage_review_export_csv': True}, {'right_transfer_jupyter_nominative': True}, {'right_transfer_jupyter_pseudo_anonymised': True},
    #   {'right_manage_transfer_jupyter': True}, {'right_export_csv_nominative': True}, {'right_export_csv_pseudo_anonymised': True},
    #   {'right_manage_export_csv': True}, {'right_read_env_unix_users': True}, {'right_manage_env_unix_users': True},
    #   {'right_manage_env_user_links': True}, {'right_add_users': True}, {'right_edit_users': True}, {'right_read_users': True},
    #   {'right_edit_roles': True}, {'right_read_logs': True}]
    res = []
    for c_a in cs_a:
        if c_a in cs_b:
            res.append(c_a)
        else:
            to_add = False
            for c_b in cs_b:
                non_perimeter_criteria = [k for (k, v) in c_a.items() if v and 'perimeter' not in k]
                if all(c_b.get(r) for r in non_perimeter_criteria):
                    to_add = True
                    perimeter_not = c_b.get('perimeter_not', [])
                    perimeter_not.extend(c_a.get('perimeter_not', []))
                    perimeter_not_child = c_b.get('perimeter_not_child', [])
                    perimeter_not_child.extend(c_a.get('perimeter_not_child', []))
                    if perimeter_not:
                        c_b['perimeter_not'] = perimeter_not
                    if perimeter_not_child:
                        c_b['perimeter_not_child'] = perimeter_not_child
                    c_a.update(c_b)
            if to_add:
                res.append(c_a)
    return res


def check_accesses_managing_roles(access: Access, perimeter: Perimeter, readonly: bool):
    role = access.role

    if access.perimeter == perimeter:
        has_admin_accesses_managing_role = readonly and role.right_read_admin_accesses_same_level or role.right_manage_admin_accesses_same_level
        has_data_accesses_managing_role = readonly and role.right_read_data_accesses_same_level or role.right_manage_data_accesses_same_level
    elif access.perimeter.level > perimeter.level:
        has_admin_accesses_managing_role = (readonly and role.right_read_admin_accesses_inferior_levels
                                            or role.right_manage_admin_accesses_inferior_levels)
        has_data_accesses_managing_role = (readonly and role.right_read_data_accesses_inferior_levels
                                           or role.right_manage_data_accesses_inferior_levels)
    else:
        has_admin_accesses_managing_role = False
        has_data_accesses_managing_role = False
    return has_admin_accesses_managing_role, has_data_accesses_managing_role


def do_user_accesses_allow_to_manage_role(user: User, role: Role, perimeter: Perimeter, readonly: bool = False) -> bool:
    has_full_admin_role = False
    has_admin_accesses_managing_role = False
    has_data_accesses_managing_role = False
    has_jupyter_accesses_managing_role = False
    has_csv_accesses_managing_role = False

    user_accesses = get_all_user_managing_accesses_on_perimeter(user, perimeter)

    for access in user_accesses:
        role = access.role
        has_admin_accesses_managing_role_2, has_data_accesses_managing_role_2 = check_accesses_managing_roles(access=access,
                                                                                                              perimeter=perimeter,
                                                                                                              readonly=readonly)
        has_full_admin_role = has_full_admin_role or role.right_full_admin
        has_admin_accesses_managing_role = has_admin_accesses_managing_role or has_admin_accesses_managing_role_2
        has_data_accesses_managing_role = has_data_accesses_managing_role or has_data_accesses_managing_role_2
        has_jupyter_accesses_managing_role = has_jupyter_accesses_managing_role or role.right_manage_export_jupyter_accesses
        has_csv_accesses_managing_role = has_csv_accesses_managing_role or role.right_manage_export_csv_accesses

    return (has_full_admin_role or not role.requires_full_admin_role_to_be_managed) \
        and (has_admin_accesses_managing_role or not role.requires_admin_accesses_managing_role_to_be_managed) \
        and (has_data_accesses_managing_role or not role.requires_data_accesses_managing_role_to_be_managed) \
        and (has_jupyter_accesses_managing_role or not role.requires_jupyter_accesses_managing_role_to_be_managed) \
        and (has_csv_accesses_managing_role or not role.requires_csv_accesses_managing_role_to_be_managed)


def get_all_user_managing_accesses_on_perimeter(user: User, perimeter: Perimeter) -> QuerySet:
    """
    filter user's valid accesses to extract:
        those configured directly on the given perimeter AND allow to read/manage accesses on the same level
      + those configured on any of the perimeter's parents AND allow to read/manage accesses on inferior levels
      + those allowing to read/manage accesses on any level
    """

    return get_user_valid_manual_accesses(user).filter((Q(perimeter=perimeter) & Role.q_allow_manage_accesses_on_same_level())
                                                       | (perimeter.all_parents_query("perimeter") & Role.q_allow_manage_accesses_on_inf_levels())
                                                       | Role.q_allow_manage_accesses_on_any_level())\
                                               .select_related("role")


def get_user_valid_manual_accesses(user: User) -> QuerySet:
    return Access.objects.filter(Access.q_is_valid()
                                 & Profile.q_is_valid()
                                 & Q(profile__source=MANUAL_SOURCE)
                                 & Q(profile__user=user))


def get_user_data_accesses(user: User) -> QuerySet:
    return get_user_valid_manual_accesses(user).filter(join_qs([Q(role__right_read_patient_nominative=True),
                                                                Q(role__right_read_patient_pseudonymized=True),
                                                                Q(role__right_search_patients_by_ipp=True),
                                                                Q(role__right_read_research_opposed_patient_data=True),
                                                                Q(role__right_export_csv_nominative=True),
                                                                Q(role__right_export_csv_pseudonymized=True),
                                                                Q(role__right_export_jupyter_pseudonymized=True),
                                                                Q(role__right_export_jupyter_nominative=True)]))\
                                               .prefetch_related('role')


def get_data_accesses_annotated_with_rights(user: User) -> QuerySet:
    return get_user_data_accesses(user).prefetch_related("role", "profile") \
                                       .prefetch_related(Prefetch('perimeter',
                                                                  queryset=Perimeter.objects.all().
                                                                  select_related(*["parent" + i * "__parent"
                                                                                   for i in range(0, len(PERIMETERS_TYPES) - 2)]))) \
                                       .annotate(right_read_patient_nominative=F('role__right_read_patient_nominative'),
                                                 right_read_patient_pseudonymized=F('role__right_read_patient_pseudonymized'),
                                                 right_search_patients_by_ipp=F('role__right_search_patients_by_ipp'),
                                                 right_read_research_opposed_patient_data=F('role__right_read_research_opposed_patient_data'),
                                                 right_export_csv_pseudonymized=F('role__right_export_csv_pseudonymized'),
                                                 right_export_csv_nominative=F('role__right_export_csv_nominative'),
                                                 right_export_jupyter_pseudonymized=F('role__right_export_jupyter_pseudonymized'),
                                                 right_export_jupyter_nominative=F('role__right_export_jupyter_nominative'))


def get_data_rights_from_accesses(user: User, data_accesses: QuerySet) -> List[DataRight]:
    accesses_with_reading_patient_data_rights = data_accesses.filter(join_qs([Q(role__right_read_patient_nominative=True),
                                                                              Q(role__right_read_patient_pseudonymized=True),
                                                                              Q(role__right_search_patients_by_ipp=True),
                                                                              Q(role__right_read_research_opposed_patient_data=True)]))
    return [DataRight(user_id=user.pk, perimeter=access.perimeter, reading_rights=access.__dict__)
            for access in accesses_with_reading_patient_data_rights]


def get_data_rights_for_target_perimeters(user: User, target_perimeters: QuerySet) -> List[DataRight]:
    return [DataRight(user_id=user.pk, perimeter=perimeter, reading_rights=None)
            for perimeter in target_perimeters]


def group_data_rights_by_perimeter(data_rights: List[DataRight]) -> Dict[int, DataRight]:
    data_rights_per_perimeter = {}
    for dr in data_rights:
        perimeter_id = dr.perimeter.id
        if perimeter_id not in data_rights_per_perimeter:
            data_rights_per_perimeter[perimeter_id] = dr
        else:
            data_rights_per_perimeter[perimeter_id].acquire_extra_data_reading_rights(dr=dr)
    return data_rights_per_perimeter


def share_data_reading_rights_over_relative_hierarchy(data_rights_per_perimeter: Dict[int, DataRight]) -> List[DataRight]:
    processed_perimeters = []

    for perimeter_id, data_right in data_rights_per_perimeter.items():
        if perimeter_id in processed_perimeters:
            continue
        processed_perimeters.append(perimeter_id)

        parental_chain = [data_right]

        parent_perimeter = Perimeter.objects.get(pk=perimeter_id).parent
        while parent_perimeter:
            parent_data_right = data_rights_per_perimeter.get(parent_perimeter.id)
            if not parent_data_right:
                parent_perimeter = parent_perimeter.parent
                continue

            for dr in parental_chain:
                dr.acquire_extra_data_reading_rights(dr=parent_data_right)

            parental_chain.append(parent_data_right)

            if parent_perimeter.id in processed_perimeters:
                break
            processed_perimeters.append(parent_perimeter.id)
            parent_perimeter = parent_perimeter.parent
    return list(data_rights_per_perimeter.values())


def share_global_rights_over_relative_hierarchy(user: User, data_rights: List[DataRight], data_accesses: QuerySet[Access]):
    for access in data_accesses.filter(join_qs([Q(role__right_export_csv_nominative=True),
                                                Q(role__right_export_csv_pseudonymized=True),
                                                Q(role__right_export_jupyter_nominative=True),
                                                Q(role__right_export_jupyter_pseudonymized=True)])):
        global_dr = DataRight(user_id=user.pk,
                              reading_rights=access.__dict__,
                              perimeter=None)
        for dr in data_rights:
            dr.acquire_extra_global_rights(global_dr)


def get_data_reading_rights(user: User, target_perimeters_ids: List[int]) -> List[DataRight]:
    data_accesses = get_data_accesses_annotated_with_rights(user)
    target_perimeters = Perimeter.objects.filter(id__in=target_perimeters_ids)\
                                         .select_related(*[f"parent{i * '__parent'}" for i in range(0, len(PERIMETERS_TYPES) - 2)])

    data_rights_from_accesses = get_data_rights_from_accesses(user=user,
                                                              data_accesses=data_accesses)
    data_rights_for_perimeters = []
    if target_perimeters:
        data_rights_for_perimeters = get_data_rights_for_target_perimeters(user=user,
                                                                           target_perimeters=target_perimeters)
    data_rights_per_perimeter = group_data_rights_by_perimeter(data_rights=data_rights_from_accesses + data_rights_for_perimeters)

    data_rights = share_data_reading_rights_over_relative_hierarchy(data_rights_per_perimeter=data_rights_per_perimeter)

    share_global_rights_over_relative_hierarchy(user=user,
                                                data_rights=data_rights,
                                                data_accesses=data_accesses)
    if target_perimeters:
        data_rights = filter(lambda dr: dr.perimeter in target_perimeters, data_rights)

    return [dr for dr in data_rights if any((dr.right_read_patient_nominative,
                                             dr.right_read_patient_pseudonymized,
                                             dr.right_search_patients_by_ipp,
                                             dr.right_read_research_opposed_patient_data))]


class DataRight:
    def __init__(self, user_id: str, perimeter: Perimeter = None, reading_rights: dict = None):
        reading_rights = reading_rights or {}
        self.user_id = user_id
        self.perimeter = perimeter
        self.right_read_patient_nominative = reading_rights.get("right_read_patient_nominative", False)
        self.right_read_patient_pseudonymized = reading_rights.get("right_read_patient_pseudonymized", False)
        self.right_search_patients_by_ipp = reading_rights.get("right_search_patients_by_ipp", False)
        self.right_read_research_opposed_patient_data = reading_rights.get("right_read_research_opposed_patient_data", False)
        self.right_export_csv_nominative = reading_rights.get("right_export_csv_nominative", False)
        self.right_export_csv_pseudonymized = reading_rights.get("exp_csv_pseudo", False)
        self.right_export_jupyter_nominative = reading_rights.get("right_export_csv_pseudonymized", False)
        self.right_export_jupyter_pseudonymized = reading_rights.get("right_export_jupyter_pseudonymized", False)

    def acquire_extra_data_reading_rights(self, dr: DataRight):
        self.right_read_patient_nominative = self.right_read_patient_nominative or dr.right_read_patient_nominative
        self.right_read_patient_pseudonymized = self.right_read_patient_pseudonymized or dr.right_read_patient_pseudonymized
        self.right_search_patients_by_ipp = self.right_search_patients_by_ipp or dr.right_search_patients_by_ipp
        self.right_read_research_opposed_patient_data = self.right_read_research_opposed_patient_data or dr.right_read_research_opposed_patient_data

    def acquire_extra_global_rights(self, dr: DataRight):
        self.right_export_csv_nominative = self.right_export_csv_nominative or dr.right_export_csv_nominative
        self.right_export_csv_pseudonymized = self.right_export_csv_pseudonymized or dr.right_export_csv_pseudonymized
        self.right_export_jupyter_nominative = self.right_export_jupyter_nominative or dr.right_export_jupyter_nominative
        self.right_export_jupyter_pseudonymized = self.right_export_jupyter_pseudonymized or dr.right_export_jupyter_pseudonymized
