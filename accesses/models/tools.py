from __future__ import annotations

from typing import List, Dict

from django.db.models import Q, F
from django.db.models.query import QuerySet, Prefetch
from django.utils import timezone

from accesses.models import Profile
from accesses.models.access import Access
from accesses.models.perimeter import Perimeter
from accesses.models.role import Role
from accesses.rights import all_rights
from admin_cohort.models import User
from admin_cohort.settings import MANUAL_SOURCE, PERIMETERS_TYPES
from admin_cohort.tools import join_qs


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
                                                       | Role.q_manage_accesses_on_any_level())\
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
                                                                Q(role__right_export_jupyter_nominative=True)]
                                                               ))\
                                               .prefetch_related('role')


class DataRight:     # todo: understand this
    def __init__(self,
                 perimeter_id: int,
                 user_id: str,
                 provider_id: str,
                 access_ids: List[int] = None,
                 nomi: bool = False,
                 pseudo: bool = False,
                 search_ipp: bool = False,
                 read_opposing: bool = False,
                 exp_csv_nomi: bool = False,
                 exp_csv_pseudo: bool = False,
                 exp_jupy_nomi: bool = False,
                 exp_jupy_pseudo: bool = False,
                 **kwargs):
        if 'perimeter' in kwargs:
            self.perimeter: Perimeter = kwargs['perimeter']
        self.perimeter_id = perimeter_id
        self.provider_id = provider_id
        self.user_id = user_id
        self.access_ids = access_ids or []
        self.right_read_patient_nominative = nomi
        self.right_read_patient_pseudonymized = pseudo
        self.right_search_patients_by_ipp = search_ipp
        self.right_read_research_opposed_patient_data = read_opposing
        self.right_export_csv_nominative = exp_csv_nomi
        self.right_export_csv_pseudonymized = exp_csv_pseudo
        self.right_export_jupyter_nominative = exp_jupy_nomi
        self.right_export_jupyter_pseudonymized = exp_jupy_pseudo

    @property
    def rights_granted(self) -> List[str]:
        return [r for r in ['right_read_patient_nominative',
                            'right_read_patient_pseudonymized',
                            'right_search_patients_by_ipp',
                            'right_read_research_opposed_patient_data'
                            ] if getattr(self, r, False)]

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
        self.right_read_patient_pseudonymized = self.right_read_patient_pseudonymized or right.right_read_patient_pseudonymized
        self.right_search_patients_by_ipp = self.right_search_patients_by_ipp or right.right_search_patients_by_ipp
        self.right_read_research_opposed_patient_data = (self.right_read_research_opposed_patient_data
                                                         or right.right_read_research_opposed_patient_data)

    def add_global_right(self, right: DataRight):
        """
        Adds a new DataRight access id to self access_ids
        and grants new rights given by this new DataRight
        :param right: other DataRight to complete with
        :return:
        """
        self.access_ids = list(set(self.access_ids + right.access_ids))
        self.right_export_csv_nominative = self.right_export_csv_nominative or right.right_export_csv_nominative
        self.right_export_csv_pseudonymized = self.right_export_csv_pseudonymized or right.right_export_csv_pseudonymized
        self.right_export_jupyter_nominative = self.right_export_jupyter_nominative or right.right_export_jupyter_nominative
        self.right_export_jupyter_pseudonymized = self.right_export_jupyter_pseudonymized or right.right_export_jupyter_pseudonymized

    @property
    def has_data_reading_right(self):
        return self.right_read_patient_nominative \
               or self.right_read_patient_pseudonymized \
               or self.right_search_patients_by_ipp \
               or self.right_read_research_opposed_patient_data

    @property
    def has_global_data_right(self):
        return self.right_export_csv_nominative \
               or self.right_export_csv_pseudonymized \
               or self.right_export_jupyter_nominative \
               or self.right_export_jupyter_pseudonymized


def get_data_accesses_and_rights(user: User) -> List[Access]:     # todo: understand this
    """
    :param user: user to get the datarights from
    :return: user's valid accesses completed with perimeters with their parents
    prefetched and role fields useful to build DataRight
    """
    return get_user_data_accesses(user).prefetch_related("role", "profile") \
                                       .prefetch_related(Prefetch('perimeter',
                                                                  queryset=Perimeter.objects.all().
                                                                  select_related(*["parent" + i * "__parent"
                                                                                   for i in range(0, len(PERIMETERS_TYPES) - 2)]))) \
                                       .annotate(provider_id=F("profile__provider_id"),
                                                 pseudo=F('role__right_read_patient_pseudonymized'),
                                                 search_ipp=F('role__right_search_patients_by_ipp'),
                                                 nomi=F('role__right_read_patient_nominative'),
                                                 exp_pseudo=F('role__right_export_csv_pseudonymized'),
                                                 exp_nomi=F('role__right_export_csv_nominative'),
                                                 jupy_pseudo=F('role__right_export_jupyter_pseudonymized'),
                                                 jupy_nomi=F('role__right_export_jupyter_nominative'))


def merge_accesses_into_rights(user: User,
                               data_accesses: List[Access],
                               perimeters: List[Perimeter] = None) -> Dict[int, DataRight]:     # todo: understand this
    """
    Given data accesses, will merge accesses from same perimeters
    into a DataRight, not considering those
    with only global rights (exports, etc.)
    Will add empty DataRights from perimeters
    Will refer these DataRights to each perimeter_id using a dict
    :param user: user for whom we are defining the DataRights
    :param data_accesses: accesses we build the DataRights from
    :param perimeters: Perimeter we need to consider in the result
    :return: Dict binding perimeter_ids with the DataRights bound to them
    """
    data_rights_per_perimeter = {}

    def complete_rights(dr: DataRight):
        if dr.perimeter_id not in data_rights_per_perimeter:
            data_rights_per_perimeter[dr.perimeter_id] = dr
        else:
            data_rights_per_perimeter[dr.perimeter_id].add_right(dr)

    for access in data_accesses:
        data_right = DataRight(user_id=user.pk,
                               access_ids=[access.id],
                               perimeter=access.perimeter,
                               **access.__dict__)
        if data_right.has_data_reading_right:
            complete_rights(dr=data_right)

    for p in perimeters:
        complete_rights(dr=DataRight(user_id=user.pk,
                                     access_ids=[],
                                     perimeter=p,
                                     perimeter_id=p.id,
                                     provider_id=user.provider_id))
    return data_rights_per_perimeter


def complete_data_rights_and_pop_children(rights: Dict[int, DataRight],
                                          perimeters_ids: List[int],
                                          pop_children: bool) -> List[DataRight]:     # todo: understand this
    """
    Will complete DataRight given the others bound to its perimeter's parents

    If expected_perim_ids is not empty, at the end we keep only DataRight
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
    :param perimeters_ids: perimeter to keep at the end
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
    if perimeters_ids:
        res = [r for r in res if r.perimeter_id in perimeters_ids]
    if pop_children:
        res = [r for r in res if r.perimeter_id not in to_remove]
    return res


def complete_data_right_with_global_rights(user: User,
                                           rights: List[DataRight],
                                           data_accesses: List[Access]):     # todo: understand this
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


def build_data_rights(user: User, perimeters_ids: List[int] = None) -> List[DataRight]:     # todo: understand this
    """
    Define what perimeter-bound and global data right the user is granted
    If perimeters_ids is not empty, will only return the DataRights
    on these perimeters
    If pop_children, will pop redundant DataRights, that does not bring more
    than the ones from their perimeter's parents
    :param user:
    :param perimeters_ids:
    :return:
    """
    perimeters_ids = perimeters_ids or []
    data_accesses = get_data_accesses_and_rights(user)
    perimeters = Perimeter.objects.filter(id__in=perimeters_ids)\
                                  .select_related(*[f"parent{i * '__parent'}" for i in range(0, len(PERIMETERS_TYPES) - 2)])

    # we merge accesses into rights from same perimeter_id
    data_rights_per_perimeter = merge_accesses_into_rights(user=user, data_accesses=data_accesses, perimeters=perimeters)

    rights = complete_data_rights_and_pop_children(rights=data_rights_per_perimeter,
                                                   perimeters_ids=perimeters_ids,
                                                   pop_children=False)

    complete_data_right_with_global_rights(user, rights, data_accesses)

    return [r for r in rights if r.has_data_reading_right]
