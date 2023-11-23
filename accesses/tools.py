from __future__ import annotations
from datetime import date, timedelta

import urllib
from functools import reduce
from typing import List, Dict, Set

from django.db.models import Q, F, Value
from django.db.models.query import QuerySet, Prefetch

from accesses.models import Profile, Access, Role, Perimeter
from accesses.rights import all_rights, full_admin_rights, RightGroup
from admin_cohort.models import User
from admin_cohort.settings import MANUAL_SOURCE, PERIMETERS_TYPES, ACCESS_EXPIRY_FIRST_ALERT_IN_DAYS
from admin_cohort.tools import join_qs
from cohort.tools import get_list_cohort_id_care_site


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


class PerimeterReadRight:
    def __init__(self,
                 perimeter: Perimeter,
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


def get_bound_roles(user: User) -> List[Role]:
    return [access.role for access in get_user_valid_manual_accesses(user)]


def user_is_full_admin(user: User) -> bool:
    return any(filter(lambda role: role.right_full_admin, get_bound_roles(user)))


def get_assignable_roles(user: User, perimeter_id: str) -> QuerySet:
    perimeter = Perimeter.objects.get(id=perimeter_id)
    assignable_roles_ids = [role.id for role in Role.objects.all()
                            if can_user_manage_role_on_perimeter(user=user, target_role=role, target_perimeter=perimeter)]
    return Role.objects.filter(id__in=assignable_roles_ids)


def get_right_groups(role: Role, root_rg: RightGroup):
    """ get the RightGroups to which belong each activated right on the current Role."""
    groups = []
    for right in map(lambda r: r.name, root_rg.rights):
        if getattr(role, right, False):
            groups.append(root_rg)
            break
    return groups + sum([get_right_groups(role=role, root_rg=c) for c in root_rg.child_groups], [])


def get_role_unreadable_rights(role: Role) -> List[Dict]:  # todo: understand this
    criteria = [{right.name: True} for right in all_rights]
    role_right_groups = get_right_groups(role=role, root_rg=full_admin_rights)
    for rg in role_right_groups:
        rg_criteria = []
        if any(getattr(role, right.name, False) for right in rg.rights_allowing_reading_accesses):
            for child_group in rg.child_groups:
                if child_group.rights_from_child_groups:
                    not_true = dict((right.name, False) for right in child_group.rights)
                    rg_criteria.extend({right.name: True, **not_true} for right in child_group.rights_from_child_groups)
            rg_criteria.extend({right.name: True} for right in rg.unreadable_rights)
            criteria = intersect_queryset_criteria(cs_a=criteria,
                                                   cs_b=rg_criteria)
    return criteria


def access_criteria_to_exclude(access: Access) -> List[Dict]:  # todo: understand this
    role = access.role
    unreadable_rights = get_role_unreadable_rights(role=role)

    rights_allowing_to_read_accesses_on_same_level = [right.name for right in all_rights
                                                      if getattr(role, right.name, False) and (right.allow_read_accesses_on_same_level
                                                                                               or right.allow_edit_accesses_on_same_level)]
    rights_allowing_to_read_accesses_on_inferior_levels = [right.name for right in all_rights
                                                           if getattr(role, right.name, False) and (right.allow_read_accesses_on_inf_levels
                                                                                                    or right.allow_edit_accesses_on_inf_levels)]
    for right in (rights_allowing_to_read_accesses_on_same_level +
                  rights_allowing_to_read_accesses_on_inferior_levels):
        d = {right: True}
        if right in rights_allowing_to_read_accesses_on_same_level:
            d['perimeter_not'] = [access.perimeter_id]
        if right in rights_allowing_to_read_accesses_on_inferior_levels:
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
                non_perimeter_criteria = [key for (key, val) in c_a.items() if val and 'perimeter' not in key]
                non_perimeter_criteria = non_perimeter_criteria and non_perimeter_criteria[0]
                if non_perimeter_criteria and c_b.get(non_perimeter_criteria):
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


def get_user_managing_accesses_on_perimeter(user: User, perimeter: Perimeter) -> QuerySet:
    """ filter user's valid accesses to extract:
          + those configured directly on the given perimeter AND allow to manage accesses on the same level
          + those configured on any of the perimeter's parents AND allow to manage accesses on inferior levels
          + those allowing to read/manage Exports accesses (global rights, allow to manage on any level)
    """
    return get_user_valid_manual_accesses(user).filter((Q(perimeter=perimeter) & Role.q_allow_manage_accesses_on_same_level())
                                                       | (perimeter.q_all_parents() & Role.q_allow_manage_accesses_on_inf_levels())
                                                       | Role.q_allow_manage_export_accesses())\
                                               .select_related("role")


def get_user_reading_accesses_on_perimeter(user: User, perimeter: Perimeter) -> QuerySet:
    """ filter user's valid accesses to extract:
          + those configured directly on the given perimeter AND allow to read/manage accesses on the same level
          + those configured on any of the perimeter's parents AND allow to read/manage accesses on inferior levels
          + those allowing to read/manage Exports accesses (global rights, allow to manage on any level)
    """
    return get_user_valid_manual_accesses(user).filter((Q(perimeter=perimeter) & Role.q_allow_read_accesses_on_same_level())
                                                       | (perimeter.q_all_parents() & Role.q_allow_read_accesses_on_inf_levels())
                                                       | Role.q_allow_manage_export_accesses())\
                                               .select_related("role")


def is_perimeter_child_of_perimeter(child: Perimeter, parent: Perimeter):
    return child.level > parent.level and parent.id in child.above_levels


def check_accesses_managing_roles_on_perimeter(access: Access, target_perimeter: Perimeter, readonly: bool):
    role = access.role
    if access.perimeter == target_perimeter:
        has_admin_accesses_managing_role = readonly and role.right_read_admin_accesses_same_level or role.right_manage_admin_accesses_same_level
        has_data_accesses_managing_role = readonly and role.right_read_data_accesses_same_level or role.right_manage_data_accesses_same_level
    elif is_perimeter_child_of_perimeter(child=target_perimeter,
                                         parent=access.perimeter):
        has_admin_accesses_managing_role = (readonly and role.right_read_admin_accesses_inferior_levels
                                            or role.right_manage_admin_accesses_inferior_levels)
        has_data_accesses_managing_role = (readonly and role.right_read_data_accesses_inferior_levels
                                           or role.right_manage_data_accesses_inferior_levels)
    else:
        has_admin_accesses_managing_role = False
        has_data_accesses_managing_role = False
    return has_admin_accesses_managing_role, has_data_accesses_managing_role


def can_user_read_role_on_perimeter(user: User, target_role: Role, target_perimeter: Perimeter) -> bool:
    return can_user_manage_role_on_perimeter(user=user,
                                             target_role=target_role,
                                             target_perimeter=target_perimeter,
                                             readonly=True)


def can_user_manage_role_on_perimeter(user: User, target_role: Role, target_perimeter: Perimeter, readonly: bool = False) -> bool:
    if user_is_full_admin(user):
        return True
    can_manage_admin_accesses = False
    can_manage_data_accesses = False
    can_manage_jupyter_accesses = False
    can_manage_csv_accesses = False

    if not readonly:
        user_accesses = get_user_managing_accesses_on_perimeter(user=user, perimeter=target_perimeter)
    else:
        user_accesses = get_user_reading_accesses_on_perimeter(user=user, perimeter=target_perimeter)

    for access in user_accesses:
        role = access.role
        can_manage_admin_accesses_2, can_manage_data_accesses_2 = check_accesses_managing_roles_on_perimeter(access=access,
                                                                                                             target_perimeter=target_perimeter,
                                                                                                             readonly=readonly)
        can_manage_admin_accesses = can_manage_admin_accesses or can_manage_admin_accesses_2
        can_manage_data_accesses = can_manage_data_accesses or can_manage_data_accesses_2
        can_manage_jupyter_accesses = can_manage_jupyter_accesses or role.right_manage_export_jupyter_accesses
        can_manage_csv_accesses = can_manage_csv_accesses or role.right_manage_export_csv_accesses

    return not target_role.requires_full_admin_role_to_be_managed \
        and (can_manage_admin_accesses or not target_role.requires_admin_accesses_managing_role_to_be_managed) \
        and (can_manage_data_accesses or not target_role.requires_data_accesses_managing_role_to_be_managed) \
        and (can_manage_jupyter_accesses or not target_role.requires_jupyter_accesses_managing_role_to_be_managed) \
        and (can_manage_csv_accesses or not target_role.requires_csv_accesses_managing_role_to_be_managed)


def get_user_valid_manual_accesses(user: User) -> QuerySet:
    return Access.objects.filter(Access.q_is_valid()
                                 & Profile.q_is_valid(prefix="profile")
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


def get_data_reading_rights(user: User, target_perimeters_ids: str) -> List[DataRight]:
    if target_perimeters_ids:
        urldecode_perimeters = urllib.parse.unquote(urllib.parse.unquote(target_perimeters_ids))
        target_perimeters_ids = [int(i) for i in urldecode_perimeters.split(",")]
    else:
        target_perimeters_ids = []
    target_perimeters = Perimeter.objects.filter(id__in=target_perimeters_ids)\
                                         .select_related(*[f"parent{i * '__parent'}" for i in range(0, len(PERIMETERS_TYPES) - 2)])

    data_accesses = get_data_accesses_annotated_with_rights(user)
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


def get_top_perimeters_ids_same_level(same_level_perimeters_ids: Set[int], all_perimeters_ids: Set[int]) -> Set[int]:
    """
    * If any of the parent perimeters of P is already linked to an access (same level OR inferior levels),
      then, perimeter P is not the highest perimeter in its relative hierarchy (branch), i.e. one of its parents is.
    * We assume that a right of type "manage same level" allows to manage accesses on "same level" and "inferior levels".
      Given the hierarchy in the docstring bellow:
         For example, having access on P2 allows to manage accesses on inferior levels as well, in particular on P8.
         The given access on P8 is then considered redundant.
    regarding the hierarchy below, the top perimeters with accesses of type "manage same level" are: P1 and P2
    """
    top_perimeters_ids = set()
    for p in Perimeter.objects.filter(id__in=same_level_perimeters_ids):
        if any(parent_id in all_perimeters_ids for parent_id in p.above_levels):
            continue
        top_perimeters_ids.add(p.id)
    return top_perimeters_ids


def get_top_perimeter_ids_inf_levels(inf_levels_perimeters_ids: Set[int],
                                     all_perimeters_ids: Set[int],
                                     top_same_level_perimeters_ids: Set[int]) -> Set[int]:
    """
    Get the highest perimeters on which are defined accesses allowing to manage other accesses on inf levels ONLY.
    --> The manageable perimeters will be their direct children (because accesses here allow to manage on inf levels ONLY).
    regarding the hierarchy below, the top perimeters with accesses of type "manage inf levels" are the children of P0: P3, P4 and P5
    """
    top_perimeters_ids = []
    for p in Perimeter.objects.filter(id__in=inf_levels_perimeters_ids):
        # if not (p in top_same_level_perimeters_ids                                          # access defined on P with right same_level and inf_levels
        #         or any(parent_id in all_perimeters_ids for parent_id in p.above_levels)):   # at least one access is defined on one of its parents
        if p.id not in top_same_level_perimeters_ids and all(parent_id not in all_perimeters_ids for parent_id in p.above_levels):
            children_ids = p.inferior_levels
            if not children_ids:
                continue
            top_perimeters_ids.extend(children_ids)
    return set(top_perimeters_ids)


def get_top_manageable_perimeters(user: User) -> QuerySet:
    """
    todo: Either rename rights of kind "right_manage_xxx_accesses_same_level"  to  "right_manage_xxx_accesses_same_and_inf_levels"
          or alter the logic to fit what the rights describe: same_level_exclusively   or  inf_levels_exclusively   or  both
    The user has 6 accesses allowing him to manage other accesses either on same level or on inferior levels.
    Accesses are defined on perimeters: P0, P1, P2, P5, P8 and P10
                                           APHP
                 ___________________________|____________________________
                |                           |                           |
                P0 (Inf)                    P1 (Same + Inf)             P2 (Same)
       _________|__________           ______|_______           _________|__________
      |         |         |          |             |          |         |         |
      P3        P4       P5 (Same)   P6            P7       P8 (Same)   P9       P10 (Inf)
                                                                             _____|______
                                                                            |           |
                                                                            P11         P12
    """
    user_accesses = get_user_valid_manual_accesses(user=user)
    if user_is_full_admin(user=user) or all(access.role.has_any_global_management_right()
                                            and not access.role.has_any_level_dependent_management_right() for access in user_accesses):
        return Perimeter.objects.filter(parent__isnull=True)
    else:
        same_level_accesses = user_accesses.filter(Role.q_allow_manage_accesses_on_same_level())
        inf_levels_accesses = user_accesses.filter(Role.q_allow_manage_accesses_on_inf_levels())

        same_level_perimeters_ids = {access.perimeter.id for access in same_level_accesses}
        inf_levels_perimeters_ids = {access.perimeter.id for access in inf_levels_accesses}
        all_perimeters_ids = same_level_perimeters_ids.union(inf_levels_perimeters_ids)

        top_same_level_perimeters_ids = get_top_perimeters_ids_same_level(same_level_perimeters_ids=same_level_perimeters_ids,
                                                                          all_perimeters_ids=all_perimeters_ids)
        top_inf_levels_perimeters_ids = get_top_perimeter_ids_inf_levels(inf_levels_perimeters_ids=inf_levels_perimeters_ids,
                                                                         all_perimeters_ids=all_perimeters_ids,
                                                                         top_same_level_perimeters_ids=top_same_level_perimeters_ids)
        return Perimeter.objects.filter(id__in=top_same_level_perimeters_ids.union(top_inf_levels_perimeters_ids))


def get_perimeters_read_rights(target_perimeters: QuerySet,
                               top_read_nomi_perimeters_ids: List[int],
                               top_read_pseudo_perimeters_ids: List[int],
                               allow_search_by_ipp: bool,
                               allow_read_opposed_patient: bool) -> List[PerimeterReadRight]:
    perimeter_read_right_list = []

    if not (top_read_nomi_perimeters_ids or top_read_pseudo_perimeters_ids):
        return perimeter_read_right_list

    for perimeter in target_perimeters:
        perimeter_and_parents_ids = [perimeter.id] + perimeter.above_levels
        read_nomi, read_pseudo = False, False
        if any(perimeter_id in top_read_nomi_perimeters_ids for perimeter_id in perimeter_and_parents_ids):
            read_nomi, read_pseudo = True, True
        elif any(perimeter_id in top_read_pseudo_perimeters_ids for perimeter_id in perimeter_and_parents_ids):
            read_pseudo = True
        perimeter_read_right_list.append(PerimeterReadRight(perimeter=perimeter,
                                                            read_nomi=read_nomi,
                                                            read_pseudo=read_pseudo,
                                                            allow_search_by_ipp=allow_search_by_ipp,
                                                            allow_read_opposed_patient=allow_read_opposed_patient))
    return perimeter_read_right_list


def get_top_perimeters_with_right_read_nomi(read_nomi_perimeters_ids: List[int]) -> List[int]:
    """ for each perimeter with nominative read right, remove it if any of its parents has nomi access """
    for perimeter in Perimeter.objects.filter(id__in=read_nomi_perimeters_ids):
        if any(parent_id in read_nomi_perimeters_ids for parent_id in perimeter.above_levels):
            try:
                read_nomi_perimeters_ids.remove(perimeter.id)
            except ValueError:
                continue
    return read_nomi_perimeters_ids


def get_top_perimeters_with_right_read_pseudo(top_read_nomi_perimeters_ids: List[int],
                                              read_pseudo_perimeters_ids: List[int]) -> List[int]:
    """ for each perimeter with pseudo read right, remove it if it has nomi access too or if any of its parents has nomi or pseudo access """
    for perimeter in Perimeter.objects.filter(id__in=read_pseudo_perimeters_ids):
        if any((parent_id in read_pseudo_perimeters_ids
                or parent_id in top_read_nomi_perimeters_ids
                or perimeter.id in top_read_nomi_perimeters_ids) for parent_id in perimeter.above_levels):
            try:
                read_pseudo_perimeters_ids.remove(perimeter.id)
            except ValueError:
                continue
    return read_pseudo_perimeters_ids


def get_data_reading_rights_on_perimeters(user: User, target_perimeters: QuerySet):
    user_accesses = get_user_valid_manual_accesses(user=user)
    read_patient_nominative_accesses = user_accesses.filter(Role.q_allow_read_patient_data_nominative())
    read_patient_pseudo_accesses = user_accesses.filter(Role.q_allow_read_patient_data_pseudo() |
                                                        Role.q_allow_read_patient_data_nominative())
    allow_search_by_ipp = user_accesses.filter(Role.q_allow_search_patients_by_ipp()).exists()
    allow_read_opposed_patient = user_accesses.filter(Role.q_allow_read_research_opposed_patient_data()).exists()

    read_nomi_perimeters_ids = [access.perimeter_id for access in read_patient_nominative_accesses]
    read_pseudo_perimeters_ids = [access.perimeter_id for access in read_patient_pseudo_accesses]

    top_read_nomi_perimeters_ids = get_top_perimeters_with_right_read_nomi(read_nomi_perimeters_ids=read_nomi_perimeters_ids)
    top_read_pseudo_perimeters_ids = get_top_perimeters_with_right_read_pseudo(top_read_nomi_perimeters_ids=top_read_nomi_perimeters_ids,
                                                                               read_pseudo_perimeters_ids=read_pseudo_perimeters_ids)

    perimeters_read_rights = get_perimeters_read_rights(target_perimeters=target_perimeters,
                                                        top_read_nomi_perimeters_ids=top_read_nomi_perimeters_ids,
                                                        top_read_pseudo_perimeters_ids=top_read_pseudo_perimeters_ids,
                                                        allow_search_by_ipp=allow_search_by_ipp,
                                                        allow_read_opposed_patient=allow_read_opposed_patient)
    return perimeters_read_rights


def get_target_perimeters(cohort_ids: str, owner: User) -> QuerySet:
    virtual_cohort_ids = get_list_cohort_id_care_site(cohorts_ids=[int(cohort_id) for cohort_id in cohort_ids.split(",")],
                                                      all_user_cohorts=owner.user_cohorts.all())
    return Perimeter.objects.filter(cohort_id__in=virtual_cohort_ids)


def has_at_least_one_read_nominative_access(target_perimeters: QuerySet, nomi_perimeters_ids: List[int]) -> bool:
    for perimeter in target_perimeters:
        perimeter_and_parents_ids = [perimeter.id] + perimeter.above_levels
        if any(p_id in nomi_perimeters_ids for p_id in perimeter_and_parents_ids):
            return True
    return False


def can_user_read_patient_data_in_nomi(user: User, target_perimeters: QuerySet) -> bool:
    user_accesses = get_user_valid_manual_accesses(user=user)
    read_patient_data_nomi_accesses = user_accesses.filter(Role.q_allow_read_patient_data_nominative())
    nomi_perimeters_ids = [access.perimeter_id for access in read_patient_data_nomi_accesses]
    allow_read_patient_data_nomi = has_at_least_one_read_nominative_access(target_perimeters=target_perimeters,
                                                                           nomi_perimeters_ids=nomi_perimeters_ids)
    return allow_read_patient_data_nomi


def user_has_at_least_one_pseudo_access_on_target_perimeters(target_perimeters: QuerySet,
                                                             nomi_perimeters_ids: List[int],
                                                             pseudo_perimeters_ids: List[int]) -> bool:
    for perimeter in target_perimeters:
        perimeter_and_parents_ids = [perimeter.id] + perimeter.above_levels
        if any(p_id in pseudo_perimeters_ids and p_id not in nomi_perimeters_ids for p_id in perimeter_and_parents_ids):
            return True


def user_has_at_least_one_pseudo_access(nomi_perimeters_ids: List[int], pseudo_perimeters_ids: List[int]) -> bool:
    for perimeter in Perimeter.objects.filter(id__in=pseudo_perimeters_ids):
        perimeter_and_parents_ids = [perimeter.id] + perimeter.above_levels
        if all(p_id not in nomi_perimeters_ids for p_id in perimeter_and_parents_ids):
            return True
    return False


def can_user_read_patient_data_in_pseudo(user: User, target_perimeters: QuerySet) -> bool:
    user_accesses = get_user_valid_manual_accesses(user=user)
    read_patient_data_nomi_accesses = user_accesses.filter(Role.q_allow_read_patient_data_nominative())
    read_patient_data_pseudo_accesses = user_accesses.filter(Role.q_allow_read_patient_data_pseudo() |
                                                             Role.q_allow_read_patient_data_nominative())

    nomi_perimeters_ids = [access.perimeter_id for access in read_patient_data_nomi_accesses]
    pseudo_perimeters_ids = [access.perimeter_id for access in read_patient_data_pseudo_accesses]

    if target_perimeters:
        allow_read_patient_data_pseudo = user_has_at_least_one_pseudo_access_on_target_perimeters(target_perimeters=target_perimeters,
                                                                                                  nomi_perimeters_ids=nomi_perimeters_ids,
                                                                                                  pseudo_perimeters_ids=pseudo_perimeters_ids)
    else:
        allow_read_patient_data_pseudo = user_has_at_least_one_pseudo_access(nomi_perimeters_ids=nomi_perimeters_ids,
                                                                             pseudo_perimeters_ids=pseudo_perimeters_ids)
    return allow_read_patient_data_pseudo


def can_user_read_opposed_patient_data(user: User) -> bool:
    user_accesses = get_user_valid_manual_accesses(user=user)
    return user_accesses.filter(Role.q_allow_read_research_opposed_patient_data()) \
                        .exists()


def get_accesses_to_expire(user: User, accesses: QuerySet):
    today = date.today()
    expiry_date = today + timedelta(days=ACCESS_EXPIRY_FIRST_ALERT_IN_DAYS)
    to_expire_soon = Q(end_datetime__date__gte=today) & Q(end_datetime__date__lte=expiry_date)
    accesses_to_expire = accesses.filter(Q(profile__user=user) & to_expire_soon)
    if not accesses_to_expire:
        return None
    min_access_per_perimeter = {}
    for a in accesses_to_expire:
        if a.perimeter.id not in min_access_per_perimeter or \
                a.end_datetime < min_access_per_perimeter[a.perimeter.id].end_datetime:
            min_access_per_perimeter[a.perimeter.id] = a
        else:
            continue
    return min_access_per_perimeter.values()


def filter_accesses_for_user(user: User, accesses: QuerySet) -> QuerySet:
    """ filter the accesses, the user making the request, is allowed to see.
        return a QuerySet of accesses annotated with "editable" set to True or False to indicate
        to Front whether to allow the `edit`/`close` actions on access or not
    """
    editable_accesses_ids = []
    readonly_accesses_ids = []

    for access in accesses:
        if can_user_manage_role_on_perimeter(user=user, target_role=access.role, target_perimeter=access.perimeter):
            editable_accesses_ids.append(access.id)
        elif can_user_read_role_on_perimeter(user=user, target_role=access.role, target_perimeter=access.perimeter):
            readonly_accesses_ids.append(access.id)

    editable_accesses = Access.objects.filter(id__in=editable_accesses_ids).annotate(editable=Value(True))
    readonly_accesses = Access.objects.filter(id__in=readonly_accesses_ids).annotate(editable=Value(False))
    return editable_accesses.union(readonly_accesses)


def get_accesses_on_perimeter(user: User, accesses: QuerySet, perimeter_id: int) -> QuerySet:
    valid_accesses = accesses.filter(Access.q_is_valid())
    accesses_on_perimeter = valid_accesses.filter(perimeter_id=perimeter_id)
    # perimeter = Perimeter.objects.get(pk=perimeter_id)
    # user_accesses = get_user_valid_manual_accesses(user=user)
    # user_can_read_accesses_from_above_levels = user_accesses.filter(role__right_read_accesses_above_levels=True)\
    #                                                         .exists()
    # if user_can_read_accesses_from_above_levels:
    #     accesses_on_parent_perimeters = valid_accesses.filter(Q(perimeter_id__in=perimeter.above_levels)
    #                                                           & Role.q_impact_inferior_levels())
    #     accesses_on_perimeter = accesses_on_perimeter.union(accesses_on_parent_perimeters)
    return filter_accesses_for_user(user=user, accesses=accesses_on_perimeter)


def useless_exclusion_logic(user: User, queryset: QuerySet):
    user_accesses = get_user_valid_manual_accesses(user).select_related("role")
    to_exclude = [access_criteria_to_exclude(access) for access in user_accesses]
    if to_exclude:
        to_exclude = reduce(intersect_queryset_criteria, to_exclude)
        exclusion_queries = []
        for e in to_exclude:
            rights_sub_dict = {key: val for (key, val) in e.items() if 'perimeter' not in key}
            exclusion_query = Q(**{f'role__{right}': val for (right, val) in rights_sub_dict.items()})
            if e.get('perimeter_not'):
                exclusion_query = exclusion_query \
                                  & ~Q(perimeter_id__in=e['perimeter_not'])
            if e.get('perimeter_not_child'):
                exclusion_query = exclusion_query \
                                  & ~join_qs([Q(**{f"perimeter__{i * 'parent__'}id__in": e['perimeter_not_child']})
                                              for i in range(1, len(PERIMETERS_TYPES))])
            exclusion_queries.append(exclusion_query)
        queryset = exclusion_queries and queryset.exclude(join_qs(exclusion_queries)) or queryset


def check_existing_role(data: dict) -> Role:
    data.pop("name", None)
    return Role.objects.filter(**data).first()
