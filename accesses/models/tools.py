from __future__ import annotations

from typing import List, Dict

from django.db.models import Q, F
from django.db.models.query import QuerySet, Prefetch
from django.utils import timezone

from accesses.models.access import Access
from accesses.models.perimeter import Perimeter
from accesses.models.role import Role
from accesses.rights import all_rights
from admin_cohort.models import User
from admin_cohort.settings import MANUAL_SOURCE, PERIMETERS_TYPES
from admin_cohort.tools import join_qs


def intersect_queryset_criteria(cs_a: List[Dict], cs_b: List[Dict]) -> List[Dict]:
    """
    Given two lists of Role Queryset criteria
    We keep only items that are in both lists
    Item is in both lists if it has the same
    'True' factors (ex.: right_edit_roles=True)
    If an item is in both, we merge the two versions :
    - with keeping 'False' factors,
    - with extending 'perimeter_not' and 'perimeter_not_child' lists
    :param cs_a:
    :param cs_b:
    :return:
    """
    #   [{'right_manage_data_accesses_same_level': True, 'perimeter_not_child': [8312002244], 'perimeter_not': [8312002244]},
    #   {'right_read_patient_pseudo_anonymised': True, 'perimeter_not_child': [8312002244], 'perimeter_not': [8312002244]},
    #   {'right_search_patient_with_ipp': True, 'perimeter_not_child': [8312002244], 'perimeter_not': [8312002244]},
    #   {'right_read_patient_nominative': True, 'perimeter_not_child': [8312002244], 'perimeter_not': [8312002244]},
    #   {'right_read_data_accesses_inferior_levels': True, 'perimeter_not_child': [8312002244], 'perimeter_not': [8312002244]},
    #   {'right_read_data_accesses_same_level': True, 'perimeter_not_child': [8312002244], 'perimeter_not': [8312002244]},
    #   {'right_manage_data_accesses_inferior_levels': True, 'perimeter_not_child': [8312002244], 'perimeter_not': [8312002244]},
    #   {'right_read_users': True, 'perimeter_not_child': [8312002244], 'perimeter_not': [8312002244]},
    #   {'right_manage_data_accesses_same_level': True, 'perimeter_not_child': [8312002244], 'perimeter_not': [8312002244]},
    #   {'right_read_patient_pseudo_anonymised': True, 'perimeter_not_child': [8312002244], 'perimeter_not': [8312002244]},
    #   {'right_search_patient_with_ipp': True, 'perimeter_not_child': [8312002244], 'perimeter_not': [8312002244]},
    #   {'right_read_patient_nominative': True, 'perimeter_not_child': [8312002244], 'perimeter_not': [8312002244]},
    #   {'right_read_data_accesses_inferior_levels': True, 'perimeter_not_child': [8312002244], 'perimeter_not': [8312002244]},
    #   {'right_read_data_accesses_same_level': True, 'perimeter_not_child': [8312002244], 'perimeter_not': [8312002244]},
    #   {'right_manage_data_accesses_inferior_levels': True, 'perimeter_not_child': [8312002244], 'perimeter_not': [8312002244]},
    #   {'right_read_users': True, 'perimeter_not_child': [8312002244], 'perimeter_not': [8312002244]}],
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
            add = False
            for c_b in cs_b:
                non_perimeter_criteria = [k for (k, v) in c_a.items() if v and 'perimeter' not in k]
                if all(c_b.get(r) for r in non_perimeter_criteria):
                    add = True
                    perimeter_not = c_b.get('perimeter_not', [])
                    perimeter_not.extend(c_a.get('perimeter_not', []))
                    perimeter_not_child = c_b.get('perimeter_not_child', [])
                    perimeter_not_child.extend(c_a.get('perimeter_not_child', []))
                    if perimeter_not:
                        c_b['perimeter_not'] = perimeter_not
                    if perimeter_not_child:
                        c_b['perimeter_not_child'] = perimeter_not_child
                    c_a.update(c_b)
            if add:
                res.append(c_a)
    return res


def q_is_valid_profile(field_prefix: str = '') -> Q:
    """
    Returns a query Q on Profile fields (can go with a prefix)
    Filtering on validity :
    - (valid_start or manual_valid_start if exist) is before now or null
    - (valid_end or manual_valid_end if exist) is after now or null
    - (active or manual_active if exist) is True
    :param field_prefix: str set before each field in case the queryset is
    used when Profile is a related object
    :return:
    """
    now = timezone.now()
    field_prefix = f"{field_prefix}__" if field_prefix else ""
    fields = {"valid_start": f"{field_prefix}valid_start_datetime",
              "manual_valid_start": f"{field_prefix}manual_valid_start_datetime",
              "valid_end": f"{field_prefix}valid_end_datetime",
              "manual_valid_end": f"{field_prefix}manual_valid_end_datetime",
              "active": f"{field_prefix}is_active",
              "manual_active": f"{field_prefix}manual_is_active"
              }
    q_actual_start_is_none = Q(**{fields['valid_start']: None,
                                  fields['manual_valid_start']: None})
    q_start_lte_now = ((Q(**{fields['manual_valid_start']: None})
                        & Q(**{f"{fields['valid_start']}__lte": now}))
                       | Q(**{f"{fields['manual_valid_start']}__lte": now}))

    q_actual_end_is_none = Q(**{fields['valid_end']: None,
                                fields['manual_valid_end']: None})
    q_end_gte_now = ((Q(**{fields['manual_valid_end']: None})
                      & Q(**{f"{fields['valid_end']}__gte": now}))
                     | Q(**{f"{fields['manual_valid_end']}__gte": now}))

    q_is_active = ((Q(**{fields['manual_active']: None})
                    & Q(**{fields['active']: True}))
                   | Q(**{fields['manual_active']: True}))
    return ((q_actual_start_is_none | q_start_lte_now)
            & (q_actual_end_is_none | q_end_gte_now)
            & q_is_active)


def get_admin_roles(access: Access, perimeter_id: int, just_read: bool):
    role = access.role
    if access.perimeter_id == perimeter_id:
        has_admin_managing_role = just_read and role.right_read_admin_accesses_same_level or role.right_manage_admin_accesses_same_level
        has_admin_role = just_read and role.right_read_data_accesses_same_level or role.right_manage_data_accesses_same_level
    else:
        has_admin_managing_role = just_read and role.right_read_admin_accesses_inferior_levels or role.right_manage_admin_accesses_inferior_levels
        has_admin_role = just_read and role.right_read_data_accesses_inferior_levels or role.right_manage_data_accesses_inferior_levels
    return has_admin_managing_role, has_admin_role


def can_roles_manage_access(user_accesses: List[Access], role: Role, perimeter: Perimeter, just_read: bool = False) -> bool:
    """
    Given accesses from a user (perimeter + role), will determine if the user
    has specific rights to manage or read on other accesses,
    either on the perimeter or ones from inferior levels
    Then, depending on what the role requires to be managed,
    or read if just_read=True, will return if the accesses are sufficient
    @param user_accesses:
    @param role:
    @param perimeter:
    @param just_read: True if we should check the possibility to read, instead of to manage
    @return:
    """
    has_main_admin_role = False
    has_admin_managing_role = False
    has_admin_role = False
    has_jupy_rvw_mng_role = False
    has_jupy_mng_role = False
    has_csv_rvw_mng_role = False
    has_csv_mng_role = False

    for a in user_accesses:
        acc_role = a.role
        has_main_admin_role = acc_role.right_edit_roles
        has_admin_managing_role, has_admin_role = get_admin_roles(access=a, perimeter_id=perimeter.id, just_read=just_read)
        has_jupy_rvw_mng_role = acc_role.right_manage_review_transfer_jupyter
        has_jupy_mng_role = acc_role.right_manage_transfer_jupyter
        has_csv_rvw_mng_role = acc_role.right_manage_review_export_csv
        has_csv_mng_role = acc_role.right_manage_export_csv

    return (has_main_admin_role or not role.requires_main_admin_role) \
        and (has_admin_managing_role or not role.requires_admin_managing_role) \
        and (has_admin_role or not role.requires_admin_role) \
        and (has_main_admin_role or has_admin_managing_role or not role.requires_any_admin_mng_role) \
        and (has_jupy_rvw_mng_role or not role.requires_manage_review_transfer_jupyter_role) \
        and (has_jupy_mng_role or not role.requires_manage_transfer_jupyter_role) \
        and (has_csv_rvw_mng_role or not role.requires_manage_review_export_csv_role) \
        and (has_csv_mng_role or not role.requires_manage_export_csv_role)


def get_assignable_roles_on_perimeter(user: User, perimeter: Perimeter) -> List[int]:
    user_accesses = get_all_user_managing_accesses_on_perimeter(user, perimeter)
    return [r.id for r in Role.objects.all() if can_roles_manage_access(list(user_accesses), r, perimeter)]


def get_all_user_managing_accesses_on_perimeter(user: User, perimeter: Perimeter) -> QuerySet:
    """
    more than getting the access on one Perimeter
    will also get the ones from the other perimeters that contain this perimeter
    Perimeters are organised like a tree, perimeters contain other perimeters,
    and roles are thus inherited
    :param user:
    :param perimeter:
    :return:
    """

    return get_user_valid_manual_accesses(user).filter((perimeter.all_parents_query("perimeter") & Role.manage_on_lower_levels_query("role"))
                                                       | (Q(perimeter=perimeter) & Role.manage_on_same_level_query("role"))
                                                       | Role.manage_on_any_level_query("role")
                                                       ).select_related("role")


def get_user_valid_manual_accesses(user: User) -> QuerySet:
    return Access.objects.filter(q_is_valid_access()
                                 & q_is_valid_profile(field_prefix="profile")
                                 & Q(profile__source=MANUAL_SOURCE)
                                 & Q(profile__user=user))


def get_user_data_accesses_queryset(user: User) -> QuerySet:
    return get_user_valid_manual_accesses(user).filter(join_qs([Q(role__right_read_patient_nominative=True),
                                                                Q(role__right_read_patient_pseudo_anonymised=True),
                                                                Q(role__right_search_patient_with_ipp=True),
                                                                Q(role__right_export_csv_nominative=True),
                                                                Q(role__right_export_csv_pseudo_anonymised=True),
                                                                Q(role__right_transfer_jupyter_pseudo_anonymised=True),
                                                                Q(role__right_transfer_jupyter_nominative=True)]
                                                               )).prefetch_related('role')


def q_is_valid_access() -> Q:
    now = timezone.now()
    return ((Q(start_datetime=None) | Q(start_datetime__lte=now))
            & (Q(end_datetime=None) | Q(end_datetime__gte=now)))


def q_role_impacts_lower_levels() -> Q:
    prefix = "role__"
    rights_impacting_lower_levels = [right for right in all_rights if right.impact_lower_levels]
    return join_qs([Q(**{f'{prefix}{r.name}': True}) for r in rights_impacting_lower_levels])


class DataRight:
    def __init__(self, perimeter_id: int, user_id: str, provider_id: str,
                 access_ids: List[int] = None,
                 pseudo: bool = False, nomi: bool = False,
                 exp_pseudo: bool = False, exp_nomi: bool = False,
                 jupy_pseudo: bool = False, jupy_nomi: bool = False,
                 search_ipp: bool = False, **kwargs):
        if 'perimeter' in kwargs:
            self.perimeter: Perimeter = kwargs['perimeter']
        self.perimeter_id = perimeter_id
        self.provider_id = provider_id
        self.user_id = user_id
        self.access_ids = access_ids or []
        self.right_read_patient_nominative = nomi
        self.right_read_patient_pseudo_anonymised = pseudo
        self.right_search_patient_with_ipp = search_ipp
        self.right_export_csv_nominative = exp_nomi
        self.right_export_csv_pseudo_anonymised = exp_pseudo
        self.right_transfer_jupyter_nominative = jupy_nomi
        self.right_transfer_jupyter_pseudo_anonymised = jupy_pseudo

    @property
    def rights_granted(self) -> List[str]:
        return [r for r in ['right_read_patient_nominative',
                            'right_read_patient_pseudo_anonymised',
                            'right_search_patient_with_ipp'
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
        self.access_ids = list(set(self.access_ids + right.access_ids))
        self.right_read_patient_nominative = self.right_read_patient_nominative or right.right_read_patient_nominative
        self.right_read_patient_pseudo_anonymised = self.right_read_patient_pseudo_anonymised or right.right_read_patient_pseudo_anonymised
        self.right_search_patient_with_ipp = self.right_search_patient_with_ipp or right.right_search_patient_with_ipp

    def add_global_right(self, right: DataRight):
        """
        Adds a new DataRight access id to self access_ids
        and grants new rights given by this new DataRight
        :param right: other DataRight to complete with
        :return:
        """
        self.access_ids = list(set(self.access_ids + right.access_ids))
        self.right_export_csv_nominative = self.right_export_csv_nominative or right.right_export_csv_nominative
        self.right_export_csv_pseudo_anonymised = self.right_export_csv_pseudo_anonymised or right.right_export_csv_pseudo_anonymised
        self.right_transfer_jupyter_nominative = self.right_transfer_jupyter_nominative or right.right_transfer_jupyter_nominative
        self.right_transfer_jupyter_pseudo_anonymised = \
            self.right_transfer_jupyter_pseudo_anonymised or right.right_transfer_jupyter_pseudo_anonymised

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


def get_access_data_rights(user: User) -> List[Access]:
    """
    :param user: user to get the datarights from
    :return: user's valid accesses completed with perimeters with their parents
    prefetched and role fields useful to build DataRight
    """
    return get_user_data_accesses_queryset(user).prefetch_related("role", "profile") \
                                                .prefetch_related(Prefetch('perimeter',
                                                                           queryset=Perimeter.objects.all().
                                                                           select_related(*["parent" + i * "__parent"
                                                                                            for i in range(0, len(PERIMETERS_TYPES) - 2)]))) \
                                                .annotate(provider_id=F("profile__provider_id"),
                                                          pseudo=F('role__right_read_patient_pseudo_anonymised'),
                                                          search_ipp=F('role__right_search_patient_with_ipp'),
                                                          nomi=F('role__right_read_patient_nominative'),
                                                          exp_pseudo=F('role__right_export_csv_pseudo_anonymised'),
                                                          exp_nomi=F('role__right_export_csv_nominative'),
                                                          jupy_pseudo=F('role__right_transfer_jupyter_pseudo_anonymised'),
                                                          jupy_nomi=F('role__right_transfer_jupyter_nominative'))


def merge_accesses_into_rights(user: User,
                               data_accesses: List[Access],
                               expected_perims: List[Perimeter] = None) -> Dict[int, DataRight]:
    """
    Given data accesses, will merge accesses from same perimeters
    into a DataRight, not considering those
    with only global rights (exports, etc.)
    Will add empty DataRights from expected_perims
    Will refer these DataRights to each perimeter_id using a dict
    :param user: user whom we are defining the DataRights
    :param data_accesses: accesses we build the DataRights from
    :param expected_perims: Perimeter we need to consider in the result
    :return: Dict binding perimeter_ids with the DataRights bound to them
    """
    rights = {}

    def complete_rights(right: DataRight):
        if right.perimeter_id not in rights:
            rights[right.perimeter_id] = right
        else:
            rights[right.perimeter_id].add_right(right)

    for access in data_accesses:
        right = DataRight(user_id=user.pk, access_ids=[access.id], perimeter=access.perimeter, **access.__dict__)
        if right.has_data_read_right:
            complete_rights(right)

    for p in expected_perims:
        complete_rights(DataRight(user_id=user.pk, access_ids=[], perimeter=p, provider_id=user.provider_id, perimeter_id=p.id))
    return rights


def complete_data_rights_and_pop_children(rights: Dict[int, DataRight],
                                          expected_perimeters: QuerySet,
                                          pop_children: bool) -> List[DataRight]:
    """
    Will complete DataRight given the others bound to its perimeter's parents

    If expected_perimeters is not empty, at the end we keep only DataRight
    bound to them

    If pop_children is True, will also pop DataRights that are redundant given
    their perimeter's parents, following this rule :
    If a child DataRight does not have a right that a parent does not have,
    then it is removed
    With a schema : a row is a DataRight,
    columns are rights nomi, pseudo, search_ipp
    and from up to bottom is parent-to-children links,
    Ex. 1:                  Ex. 2:
    0  1  1      0  1  1    0  0  1      0  0  1
       |     ->                |
    1  1  0      1  1  1    1  0  0      1  0  1
       |                       |     ->
    0  0  1                 0  0  1
       |                       |
    1  1  1                 1  1  1      1  1  1
    :param rights: rights to read and complete
    :param expected_perimeters: perimeter to keep at the end
    :param pop_children: true if we want to clean redundant DataRights
    :return:
    """
    processed = []
    to_remove = []
    for right in rights.values():
        # if we've already processed this perimeter, it means the DataRight
        # is already completed with its parents' DataRights
        if right.perimeter_id in processed:
            continue
        processed.append(right.perimeter_id)

        # will contain each DataRight we meet following first right's parents
        parental_chain = [right]

        # we now go from parent to parent to complete each DataRight
        # inheriting from them with more granted rights
        parent_perim = right.perimeter.parent
        while parent_perim:
            parent_right = rights.get(parent_perim.id)
            if not parent_right:
                parent_perim = parent_perim.parent
                continue

            [r.add_right(parent_right) for r in parental_chain]
            parental_chain.append(parent_right)

            # if we've already processed this perimeter, it means the DataRight
            # is completed already, no need to go on with the loop
            if parent_perim.id in processed:
                break
            processed.append(parent_perim.id)
            parent_perim = parent_perim.parent

        # Now that all rights in parental_chain are completed with granted
        # rights from parent DataRights,
        # a DataRight not having more granted rights than their parent means
        # they do not bring different rights to the user on their perimeter
        biggest_rights = parental_chain[-1].count_rights_granted
        for r in parental_chain[-2::-1]:
            if r.count_rights_granted <= biggest_rights:
                to_remove.append(r.perimeter_id)

    res = list(rights.values())
    if expected_perimeters:
        res = [r for r in res if r.perimeter in expected_perimeters]
    if pop_children:
        res = [r for r in res if r.perimeter_id not in to_remove]
    return res


def complete_data_right_with_global_rights(user: User,
                                           rights: List[DataRight],
                                           data_accesses: List[Access]):
    """
    Given the user's data_accesses, filter the DataRights
    with global data rights (exports, etc.),
    and add them to the others DataRight
    :param user:
    :param rights:
    :param data_accesses:
    :return:
    """
    global_rights = list()
    for acc in data_accesses:
        dr = DataRight(user_id=user.pk, access_ids=[acc.id], perimeter=acc.perimeter, **acc.__dict__)
        if dr.has_global_data_right:
            global_rights.append(dr)

    for r in rights:
        for plr in global_rights:
            r.add_global_right(plr)


def build_data_rights(user: User, expected_perimeters_ids: List[int] = None, pop_children: bool = False) -> List[DataRight]:
    """
    Define what perimeter-bound and global data right the user is granted
    If expected_perimeters_ids is not empty, will only return the DataRights
    on these perimeters
    If pop_children, will pop redundant DataRights, that does not bring more
    than the ones from their perimeter's parents
    :param user:
    :param expected_perimeters_ids:
    :param pop_children:
    :return:
    """
    expected_perimeters_ids = expected_perimeters_ids or []
    data_accesses = get_access_data_rights(user)
    expected_perimeters = Perimeter.objects.filter(id__in=expected_perimeters_ids)\
                                           .select_related(*[f"parent{i * '__parent'}" for i in range(0, len(PERIMETERS_TYPES) - 2)])

    # we merge accesses into rights from same perimeter_id
    rights = merge_accesses_into_rights(user, data_accesses, expected_perimeters)

    rights = complete_data_rights_and_pop_children(rights, expected_perimeters, pop_children)

    complete_data_right_with_global_rights(user, rights, data_accesses)

    return [r for r in rights if r.has_data_read_right]
