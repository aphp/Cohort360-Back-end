from __future__ import annotations

import datetime
import json
import random
from datetime import timedelta

from itertools import product, combinations
from typing import List, Union

from django.utils import timezone
from rest_framework import status as http_status
from rest_framework.test import force_authenticate

from accesses.models import Access, Role, Profile, Perimeter
from accesses.rights import main_admin_rights, admin_manager_rights,\
    csv_export_manage_rights, jup_export_manage_rights,\
    csv_review_manage_rights, workspaces_rights, user_rights,\
    data_admin_rights, data_rights, csv_export_rights, jup_export_rights,\
    jup_review_rights, csv_review_rights, right_read_users,\
    jup_review_manage_rights
from accesses.views import AccessViewSet
from admin_cohort.settings import MANUAL_SOURCE
from admin_cohort.tools.tests_tools import new_user_and_profile, CaseRetrieveFilter, \
    ViewSetTestsWithBasicPerims, RequestCase, ALL_RIGHTS, DeleteCase, \
    PatchCase, CreateCase, ListCase, new_random_user
from admin_cohort.tools import prettify_dict, prettify_json


# EXPECTED READ RESULTS #######################################################


class ObjectView(object):
    def __init__(self, d):
        self.__dict__ = d


class ReadObject:
    def __str__(self):
        return prettify_dict(self.__dict__)


class ReadRight(ReadObject):
    def __init__(self, o: dict):
        assert 'perimeter_id' in o
        assert 'access_ids' in o
        assert isinstance(o.get('access_ids'), list)
        assert all([isinstance(i, int) for i in o.get('access_ids')])
        assert isinstance(o.get('perimeter_id'), int)
        assert 'right_read_patient_nominative' in o
        assert isinstance(o.get('right_read_patient_nominative'), bool)
        assert 'right_read_patient_pseudo_anonymised' in o
        assert isinstance(o.get('right_read_patient_pseudo_anonymised'), bool)
        assert 'right_search_patient_with_ipp' in o
        assert isinstance(o.get('right_search_patient_with_ipp'), bool)

        assert 'right_export_csv_nominative' in o
        assert isinstance(o.get('right_export_csv_nominative'), bool)
        assert 'right_export_csv_pseudo_anonymised' in o
        assert isinstance(o.get('right_export_csv_pseudo_anonymised'), bool)
        assert 'right_transfer_jupyter_nominative' in o
        assert isinstance(o.get('right_transfer_jupyter_nominative'), bool)
        assert 'right_transfer_jupyter_pseudo_anonymised' in o
        assert isinstance(o.get('right_transfer_jupyter_pseudo_anonymised'),
                          bool)

        self.perimeter_id: int = o.get('perimeter_id')
        self.access_ids: List[int] = o.get('access_ids')
        self.right_read_patient_nominative: bool = \
            o.get('right_read_patient_nominative')
        self.right_read_patient_pseudo_anonymised: bool = \
            o.get('right_read_patient_pseudo_anonymised')
        self.right_search_patient_with_ipp: bool = \
            o.get('right_search_patient_with_ipp')
        self.right_export_csv_nominative: bool = \
            o.get('right_export_csv_nominative')
        self.right_export_csv_pseudo_anonymised: bool = \
            o.get('right_export_csv_pseudo_anonymised')
        self.right_transfer_jupyter_nominative: bool = \
            o.get('right_transfer_jupyter_nominative')
        self.right_transfer_jupyter_pseudo_anonymised: bool = \
            o.get('right_transfer_jupyter_pseudo_anonymised')

    def match(self, other_right: ReadRight) -> bool:
        return self.perimeter_id == other_right.perimeter_id \
               and self.right_read_patient_nominative == \
               other_right.right_read_patient_nominative \
               and self.right_read_patient_pseudo_anonymised == \
               other_right.right_read_patient_pseudo_anonymised \
               and self.right_search_patient_with_ipp == \
               other_right.right_search_patient_with_ipp \
               and self.right_export_csv_nominative == \
               other_right.right_export_csv_nominative \
               and self.right_export_csv_pseudo_anonymised == \
               other_right.right_export_csv_pseudo_anonymised \
               and self.right_transfer_jupyter_nominative == \
               other_right.right_transfer_jupyter_nominative \
               and self.right_transfer_jupyter_pseudo_anonymised == \
               other_right.right_transfer_jupyter_pseudo_anonymised \
               and all([i in other_right.access_ids for i in self.access_ids]) \
               and len(self.access_ids) == len(other_right.access_ids)


class ReadAccess(ReadObject):
    def __init__(self, o: dict):
        check_dct = dict(
            id=int,
            is_valid=bool,
            profile=dict,
            role=dict,
            perimeter=dict,
            perimeter_id=str,
        )
        for (k, t) in check_dct.items():
            assert k in o
            assert isinstance(o.get(k), t)
            setattr(self, k, o.get(k))

        for dt_field in ["start_datetime", "end_datetime"]:
            assert dt_field in o
            v = o.get(dt_field)
            assert isinstance(v, (type(None), str))
            if v:
                try:
                    timezone.datetime.fromisoformat(v.replace("Z", "+00:00"))
                except (TypeError, ValueError) as e:
                    raise ValueError(f"Datetime unreadable for {dt_field}: {v} - {e}")
            setattr(self, dt_field, v)


# TEST CASES #################################################################


class AccessCaseRetrieveFilter(CaseRetrieveFilter):
    def __init__(self, perimeter_id: str = "",
                 role: Role = None, profile: Profile = None, **kwargs):
        self.perimeter_id = perimeter_id
        self.role = kwargs.get('role_id', role.id if role else None)
        self.profile = kwargs.get('profile_id', profile.id if profile else None)
        super(AccessCaseRetrieveFilter, self).__init__(**kwargs)


class AccessCase:
    def __init__(self, user_rights: List[str] = None,
                 user_profile: Profile = None, user_perimeter: Perimeter = None
                 ):
        self.user_rights = user_rights
        self.user_perimeter = user_perimeter
        self.user_profile = user_profile


class AccessListCase(ListCase, AccessCase):
    def __init__(self, user_rights: List[str] = None,
                 user_profile: Profile = None, user_perimeter: Perimeter = None,
                 **kwargs):
        AccessCase.__init__(self, user_rights, user_profile, user_perimeter)
        super(AccessListCase, self).__init__(**kwargs)

    @property
    def description_dict(self):
        return {
            **super(AccessListCase, self).description_dict,
            'user_perimeter': self.user_perimeter.name,
            'user_profile': self.user_profile.provider_name,
        }

    @property
    def accessible_perimeters_ids(self):
        if "inferior" in self.name:
            list(self.user_perimeter.all_children_queryset)
        elif "same" in self.name:
            return [self.user_perimeter]
        else:
            return list(Perimeter.objects.all())


class RightListCase(ListCase):
    def __init__(self, user_rights: List[str] = None,
                 user_profile: Profile = None, user_perimeter: Perimeter = None,
                 to_find: List[ReadRight] = None,
                 **kwargs):
        super(RightListCase, self).__init__(to_find, **kwargs)

    @property
    def description_dict(self):
        d = {
            **super(RightListCase, self).description_dict,
            'to_find': ([obj.__dict__ for obj in self.to_find[0:10]]
                        + (["..."] if len(self.to_find) > 10 else [])),
        }
        return d


class AccessCreateCase(CreateCase, AccessCase):
    def __init__(self, data: dict, user_profile: Profile,
                 user_perimeter: Perimeter, user_rights: List[str] = None,
                 **kwargs):
        AccessCase.__init__(self, user_rights, user_profile, user_perimeter)
        super(AccessCreateCase, self).__init__(
            **{
                **kwargs,
                'retrieve_filter': AccessCaseRetrieveFilter(**data),
                'data': data
            })

    def clone(self, **kwargs) -> AccessCreateCase:
        return self.__class__(**{**self.__dict__, **kwargs})

    @property
    def description_dict(self) -> dict:
        d = {
            **super(AccessCreateCase, self).description_dict,
            'user_perimeter': self.user_perimeter.name,
            'user_profile': self.user_profile.source,
        }
        d.pop('retrieve_filter', None)
        return d


class AccessDeleteCase(DeleteCase, AccessCase):
    def __init__(self, data_to_delete: dict, user_profile: Profile,
                 user_perimeter: Perimeter, user_rights: List[str] = None,
                 **kwargs):
        AccessCase.__init__(self, user_rights, user_profile, user_perimeter)
        super(AccessDeleteCase, self).__init__(
            data_to_delete=data_to_delete, **kwargs)

    def clone(self, **kwargs) -> AccessDeleteCase:
        return self.__class__(**{**self.__dict__, **kwargs})

    @property
    def description_dict(self) -> dict:
        d = {
            **super(AccessDeleteCase, self).description_dict,
            'user_perimeter': self.user_perimeter.name,
            'user_profile': self.user_profile.source,
        }
        d.pop('retrieve_filter', None)
        return d


class AccessPatchCase(PatchCase, AccessCase):
    def __init__(self, initial_data: dict, user_profile: Profile,
                 user_perimeter: Perimeter, user_rights: List[str] = None,
                 **kwargs):
        AccessCase.__init__(self, user_rights, user_profile, user_perimeter)
        super(AccessPatchCase, self).__init__(
            initial_data=initial_data, **kwargs)

    def clone(self, **kwargs) -> AccessPatchCase:
        return self.__class__(**{**self.__dict__, **kwargs})


class AccessCloseCase(RequestCase, AccessCase):
    def __init__(self, initial_data: dict, user_profile: Profile = None,
                 user_perimeter: Perimeter = None,
                 user_rights: List[str] = None, **kwargs):
        AccessCase.__init__(self, user_rights, user_profile, user_perimeter)
        super(AccessCloseCase, self).__init__(**kwargs)
        self.initial_data = initial_data

    def clone(self, **kwargs) -> AccessCloseCase:
        return self.__class__(**{**self.__dict__, **kwargs})

    def description_dict(self) -> dict:
        d = {
            **super(AccessCloseCase, self).description_dict,
            'user_perimeter': self.user_perimeter.name,
            'user_profile': self.user_profile.source,
        }
        d.pop('retrieve_filter', None)
        return d


# RIGHTS DESCRIPTION ###########################################################


class RightGroup:
    def __init__(self, name: str, rights: List[str], is_manager_admin: bool,
                 same_level_reader: str = "", inf_level_reader: str = "",
                 same_level_editor: str = "", inf_level_editor: str = "",
                 children: List = None, has_parent: bool = True):
        self.name = name
        self.rights = rights or []
        self.is_manager_admin = is_manager_admin
        self.same_level_reader = same_level_reader
        self.inf_level_reader = inf_level_reader
        self.same_level_editor = same_level_editor
        self.inf_level_editor = inf_level_editor
        self.children = children
        self.has_parent = has_parent

    def __str__(self):
        return self.name

    def all_children_rights(self, r: bool = True,
                            exempt: str = "") -> List[str]:
        """
        Return all 'rights' values from items in self.children
        @param r: makes it recursive (getting 'rights' from children.children
        @param exempt: exempt one child  of the name given
        @return: list of rights from self.children
        """
        return sum([
            child.rights + (child.all_children_rights() if r else [])
            for child in self.children
            if (not exempt or exempt != child.name)
        ], [])

    def clone(self) -> RightGroup:
        new = self.__class__(name=self.name, rights=self.rights,
                             is_manager_admin=self.is_manager_admin)
        new.children = [child.clone() for child in (self.children or [])]
        [setattr(new, k, f) for (k, f) in self.__dict__.items() if
         k != 'children']
        return new


class RightGroupForList(RightGroup):
    _readable_accesses = None

    def __init__(self, children: List = None, **kwargs):
        super(RightGroupForList, self).__init__(**kwargs)

        self.children: List[RightGroupForList] = children or []
        self.any_accesses: List[Access] = []
        self.full_accesses_with_children: List[Access] = None
        self.siblings_rights: List[str] = []
        self.full_accesses_with_siblings: List[Access] = []
        self.full_accesses_with_parent: List[Access] = []
        self.full_accesses_with_parent_siblings: List[Access] = []

    def clone(self) -> RightGroupForList:
        return super(RightGroupForList, self).clone()

    @classmethod
    def clone_from_right_group(cls, rg: RightGroup) -> RightGroupForList:
        return cls(**{**rg.__dict__,
                      'children': [cls.clone_from_right_group(c)
                                   for c in (rg.children or [])]})

    def readable_accesses_with_other_rg(
            self, other: RightGroupForList) -> List[Access]:
        to_add = []

        if other in self.children:
            to_add.extend(sum([other_c.full_accesses_with_parent_siblings
                               for other_c in other.children], []))
        if self in other.children:
            to_add.extend(sum([self_c.full_accesses_with_parent_siblings
                               for self_c in self.children], []))

        return list(set(to_add))

    @property
    def readable_accesses(self) -> List[Access]:
        if self._readable_accesses is None:
            readable_accesses = sum([
                child.any_accesses + child.full_accesses_with_children
                + child.full_accesses_with_siblings
                + sum([g_child.full_accesses_with_parent
                       for g_child in child.children], [])
                for child in self.children
            ], [])

            if not self.has_parent:
                readable_accesses.extend([
                    *self.any_accesses, *self.full_accesses_with_children,
                    *sum([child.full_accesses_with_parent
                          for child in self.children], [])
                ])

            self._readable_accesses = readable_accesses

        return self._readable_accesses


class RightGroupForManage(RightGroup):
    def __init__(self, children: List = None, **kwargs):
        super(RightGroupForManage, self).__init__(**kwargs)
        self.children: List[RightGroupForManage] = children or []

        self.full_role: Role = None
        self.full_role_with_any_from_child: List[Role] = []
        self.full_role_with_any_from_direct_child: List[Role] = []
        self.full_role_with_any_from_parent: List[Role] = []
        self.full_role_with_any_from_siblings: List[Role] = []

    def clone(self) -> RightGroupForManage:
        return super(RightGroupForManage, self).clone()

    @classmethod
    def clone_from_right_group(cls, rg: RightGroup) -> RightGroupForManage:
        return cls(**{**rg.__dict__,
                      'children': [cls.clone_from_right_group(c)
                                   for c in (rg.children or [])]})

    @property
    def unmanageable_roles(self):
        unmanageable_roles = sum([
            child.full_role_with_any_from_child
            for child in self.children
        ], [])

        if self.has_parent:
            unmanageable_roles.extend([
                *sum([child.full_role_with_any_from_parent
                      for child in self.children], [])
            ])

        return unmanageable_roles

    @property
    def manageable_roles(self):
        manageable_roles = sum([
            [child.full_role] + child.full_role_with_any_from_siblings
            for child in self.children
        ], [])

        if not self.has_parent:
            manageable_roles.extend([
                self.full_role,
                *self.full_role_with_any_from_direct_child,
                *sum([child.full_role_with_any_from_parent
                      for child in self.children], [])
            ])

        return manageable_roles

    @property
    def unreadable_roles(self) -> List[Role]:
        unreadable_roles = []

        if self.has_parent:
            unreadable_roles.extend([
                self.full_role, *self.full_role_with_any_from_child,
                self.full_role_with_any_from_siblings,
                *sum([child.full_role_with_any_from_parent
                      for child in self.children], [])
            ])

        return unreadable_roles


RIGHT_GROUPS = RightGroup(
    name="RoleEditor",
    rights=main_admin_rights.rights_names,
    is_manager_admin=True,
    has_parent=False,
    children=[RightGroup(
        name="AdminManager",
        rights=admin_manager_rights.rights_names,
        is_manager_admin=True,
        same_level_reader="right_read_admin_accesses_same_level",
        inf_level_reader="right_read_admin_accesses_inferior_levels",
        same_level_editor="right_manage_admin_accesses_same_level",
        inf_level_editor="right_manage_admin_accesses_inferior_levels",
        children=[RightGroup(
            name="DataReadersAdmin",
            rights=data_admin_rights.rights_names,
            is_manager_admin=False,
            same_level_reader="right_read_data_accesses_same_level",
            inf_level_reader="right_read_data_accesses_inferior_levels",
            same_level_editor="right_manage_data_accesses_same_level",
            inf_level_editor="right_manage_data_accesses_inferior_levels",
            children=[RightGroup(
                name="DataReader",
                rights=data_rights.rights_names,
                is_manager_admin=False,
            )]
        )]
    ), RightGroup(
        name="CsvExportersAdmin",
        rights=csv_export_manage_rights.rights_names,
        is_manager_admin=False,
        children=[RightGroup(
            name="CsvExporters",
            rights=csv_export_rights.rights_names,
            is_manager_admin=False,
        )],
    ), RightGroup(
        name="JupyterExportersAdmin",
        rights=jup_export_manage_rights.rights_names,
        is_manager_admin=False,
        children=[RightGroup(
            name="JupyterExporters",
            rights=jup_export_rights.rights_names,
            is_manager_admin=False,
        )],
    ), RightGroup(
        name="CsvExportReviewersAdmin",
        rights=csv_review_manage_rights.rights_names,
        is_manager_admin=False,
        children=[RightGroup(
            name="CsvExportReviewers",
            rights=csv_review_rights.rights_names,
            is_manager_admin=False,
        )]
    ), RightGroup(
        name="JupyterExportReviewersAdmin",
        rights=jup_review_manage_rights.rights_names,
        is_manager_admin=False,
        children=[RightGroup(
            name="JupyterExportReviewers",
            rights=jup_review_rights.rights_names,
            is_manager_admin=False,
        )]
    ), RightGroup(
        name="WorkspacesManager",
        rights=workspaces_rights.rights_names,
        is_manager_admin=False,
    ), RightGroup(
        name="UsersAdmin",
        rights=user_rights.rights_names,
        is_manager_admin=False,
    )]
)

# rights that can be read with any manager manager role (because any manager
# could have it
any_manager_rights = [right_read_users.name]


# ACTUAL TESTS #################################################################


class AccessTests(ViewSetTestsWithBasicPerims):
    unupdatable_fields = ["role", "start_datetime", "end_datetime",
                          "perimeter_id", "profile"]
    unsettable_default_fields = dict(source=MANUAL_SOURCE, )
    unsettable_fields = ["id"]
    manual_dupplicated_fields = ['start_datetime', 'end_datetime']

    objects_url = "/accesses/"
    retrieve_view = AccessViewSet.as_view({'get': 'retrieve'})
    list_view = AccessViewSet.as_view({'get': 'list'})
    create_view = AccessViewSet.as_view({'post': 'create'})
    delete_view = AccessViewSet.as_view({'delete': 'destroy'})
    update_view = AccessViewSet.as_view({'patch': 'partial_update'})
    close_view = AccessViewSet.as_view({'patch': 'close'})
    model = Access
    model_objects = Access.objects
    model_fields = Access._meta.fields

    def setUp(self):
        super(AccessTests, self).setUp()

        # ROLES
        self.role_full: Role = Role.objects.create(**dict([
            (f, True) for f in ALL_RIGHTS
        ]), name='FULL')
        self.role_empty: Role = Role.objects.create(**dict([
            (f, False) for f in ALL_RIGHTS
        ]), name='EMPTY')

        # USERS
        self.admin_user, self.admin_profile = new_user_and_profile(
            p_name='admin', provider_id=1000000,
            firstname="Cid", lastname="Kramer", email='cid@aphp.fr'
        )
        self.user1, self.profile1 = new_user_and_profile(
            p_name='user1', provider_id=2000000,
            firstname="Squall", lastname="Leonheart", email='s.l@aphp.fr'
        )
        self.user2, self.profile2 = new_user_and_profile(
            p_name='user2', provider_id=3000000,
            firstname="Seifer", lastname="Almasy", email='s.a@aphp.fr'
        )

    def check_close_case(self, case: AccessCloseCase):
        user_access: Union[Access, None] = None
        if case.user_rights:
            r = Role.objects.create(**dict([(r, True) for r in case.user_rights]))
            user_access = Access.objects.create(role=r, profile=case.user_profile, perimeter=case.user_perimeter)

        acc = Access.objects.create(**case.initial_data)
        acc_id = acc.id

        request = self.factory.patch(self.objects_url)
        force_authenticate(request, case.user)
        response = self.__class__.close_view(request, id=acc_id)
        response.render()

        self.assertEqual(
            response.status_code, case.status,
            prettify_json(response.content) if response.content else None
        )
        access = Access.objects.filter(id=acc_id).first()

        if case.success:
            delta = (access.end_datetime - timezone.now())
            self.assertAlmostEqual(delta.total_seconds(), 0, delta=1)
        else:
            self.assertEqual(
                access.end_datetime, acc.end_datetime
            )

        if user_access:
            user_access.delete()

    def check_create_case(self, case: Union[AccessCreateCase, CreateCase]):
        if isinstance(case, AccessCreateCase):
            r = Role.objects.create(**dict([(r, True)
                                            for r in case.user_rights]))
            user_access: Access = Access.objects.create(
                role=r, profile=case.user_profile,
                perimeter=case.user_perimeter)

            super(AccessTests, self).check_create_case(case)
            user_access.delete()
        else:
            super(AccessTests, self).check_create_case(case)

    def check_delete_case(self, case: Union[AccessDeleteCase, DeleteCase]):
        if isinstance(case, AccessDeleteCase):
            r = Role.objects.create(**dict([(r, True)
                                            for r in case.user_rights]))
            user_access: Access = Access.objects.create(
                role=r, profile=case.user_profile,
                perimeter=case.user_perimeter)

            super(AccessTests, self).check_delete_case(case)
            user_access.delete()
        else:
            super(AccessTests, self).check_delete_case(case)

    def check_patch_case(self, case: Union[AccessPatchCase, PatchCase]):
        if isinstance(case, AccessPatchCase):
            r = Role.objects.create(**dict([(r, True)
                                            for r in case.user_rights]))
            user_access: Access = Access.objects.create(
                role=r, profile=case.user_profile,
                perimeter=case.user_perimeter)

            super(AccessTests, self).check_patch_case(case)
            user_access.delete()
        else:
            super(AccessTests, self).check_patch_case(case)

    def check_get_acc_paged_list_case(
            self, case: Union[AccessListCase, ListCase]):
        if isinstance(case, AccessListCase):
            r = Role.objects.create(**dict([(r, True)
                                            for r in case.user_rights]))
            user_access: Access = Access.objects.create(
                role=r, profile=case.user_profile,
                perimeter=case.user_perimeter)
            if r.right_edit_roles:
                case.to_find.append(user_access)

            self.check_get_paged_list_case(case)
            user_access.delete()
        else:
            self.check_get_paged_list_case(case)

    def check_get_paged_list_2_role_case(
            self, case_a: AccessListCase, case_b: AccessListCase,
            additional_accesses: List[Access]):
        r_a: Role = Role.objects.filter(
            **{**dict([(r, r in case_a.user_rights)
                       for r in Role.all_rights()])}) \
            .first()
        r_b: Role = Role.objects.filter(
            **{**dict([(r, r in case_b.user_rights)
                       for r in Role.all_rights()])}) \
            .first()

        self.assertIsNotNone(r_a, msg=case_a.title)
        self.assertIsNotNone(r_b, msg=case_b.title)

        user_access_a: Access = Access.objects.create(
            role=r_a, profile=case_a.user_profile,
            perimeter=case_a.user_perimeter)
        user_access_b: Access = Access.objects.create(
            role=r_b, profile=case_b.user_profile,
            perimeter=case_b.user_perimeter)
        succ = case_a.success or case_b.success
        case = ListCase(
            success=succ,
            user=self.user2,
            status=(http_status.HTTP_200_OK if succ
                    else http_status.HTTP_403_FORBIDDEN),
            title=f"{case_a.title} & {case_b.title}",
            to_find=list(set(case_a.to_find + case_b.to_find
                             + additional_accesses)),
        )

        if len([acc for acc in case.to_find if (
                acc.role.id == r_a.id
                and acc.perimeter_id == user_access_a.perimeter_id)]):
            case.to_find.append(user_access_a)

        if len([acc for acc in case.to_find
                if (acc.role.id == r_b.id
                    and acc.perimeter_id == user_access_b.perimeter_id)]):
            case.to_find.append(user_access_b)

        self.check_get_acc_paged_list_case(case)

        user_access_a.delete()
        user_access_b.delete()


# GET

def create_accesses(roles: List[Role], profiles: List[Profile],
                    perims: List[Perimeter]) -> List[Access]:
    return Access.objects.bulk_create([
        Access(
            profile=random.choice(profiles),
            perimeter=perim,
            role=r,
            start_datetime=timezone.now() - timedelta(days=1),
            end_datetime=timezone.now() + timedelta(days=2),
        ) for (perim, r,
               # start, end
               ) in product(
            perims,
            roles,
        )
    ])


class AccessGetTests(AccessTests):
    def setUp(self):
        super(AccessGetTests, self).setUp()

        self.user_with_rnd_accesses, self.prof_with_rnd_accesses = \
            new_user_and_profile(
                p_name="NAME1",
                provider_id=3333331,
                firstname="FNaME1",
                lastname="lNaME1",
                email="maIL1")

        self.user2_with_rnd_accesses, self.prof2_with_rnd_accesses = \
            new_user_and_profile(
                p_name="NAME2",
                provider_id=3333332,
                firstname="FNaME2",
                lastname="lNaME2",
                email="maIL2",
            )
        self.right_groups_tree: RightGroupForList = \
            RightGroupForList.clone_from_right_group(RIGHT_GROUPS)

        self.profiles_for_accesses = [self.prof_with_rnd_accesses,
                                      self.prof2_with_rnd_accesses]
        self.perimeters_for_accesses = [self.hospital2, self.hospital3]

        def add_accesses_to_right_groups_tree(
                rg: RightGroupForList, parent: RightGroupForList = None
        ):
            rg.any_accesses = create_accesses([
                Role.objects.create(**{
                    'name': f"{rg.name} - any - {f}", f: True
                }) for f in rg.rights
            ], self.profiles_for_accesses, self.perimeters_for_accesses)
            rg.full_accesses_with_children = create_accesses([
                Role.objects.create(**dict(
                    [(f, True) for f in (
                            rg.rights
                            + (any_manager_rights if rg.is_manager_admin
                               else [])
                            + rg.all_children_rights()
                    )] + [('name', f"{rg.name} - full")]))
            ], self.profiles_for_accesses, self.perimeters_for_accesses)
            if parent is not None:
                rg.siblings_rights = parent.all_children_rights(
                    r=False, exempt=rg.name)

                rg.full_accesses_with_siblings = create_accesses([
                    Role.objects.create(**dict(
                        [(f, True) for f in (
                                rg.rights
                                + (any_manager_rights if rg.is_manager_admin
                                   else [])
                                + rg.siblings_rights
                        )] + [('name', f"{rg.name} - full with siblings")]
                    ))
                ], self.profiles_for_accesses, self.perimeters_for_accesses) \
                    if len(rg.siblings_rights) > 0 else []

                rg.full_accesses_with_parent = create_accesses([
                    Role.objects.create(**dict(
                        [(f, True) for f in (
                                rg.rights
                                + (any_manager_rights if rg.is_manager_admin
                                   else []) + [parent_right]
                        )] + [('name', f"{rg.name} - full with parent right "
                                       f"{parent_right}")]
                    )) for parent_right in parent.rights
                ], self.profiles_for_accesses, self.perimeters_for_accesses)
                rg.full_accesses_with_parent_siblings = create_accesses([
                    Role.objects.create(**dict(
                        [(f, True) for f in (
                                rg.rights
                                + (any_manager_rights if rg.is_manager_admin
                                   else []) + [forbidden_one]
                        )] + [('name', f"{rg.name} - full with forbidden "
                                       f"{forbidden_one}")]
                    )) for forbidden_one in parent.siblings_rights
                ], self.profiles_for_accesses, self.perimeters_for_accesses)

            for child in rg.children:
                add_accesses_to_right_groups_tree(child, rg)

        add_accesses_to_right_groups_tree(self.right_groups_tree)

    def prepare_right_group_list_case(
            self, right_group: RightGroupForList) -> List[AccessListCase]:
        case_status = (http_status.HTTP_403_FORBIDDEN
                       if len(right_group.children) == 0
                       else http_status.HTTP_200_OK)
        base_case = AccessListCase(
            success=len(right_group.children) > 0,
            user=self.user2,
            status=case_status,
            user_profile=self.profile2,
        )
        if right_group.inf_level_reader and right_group.same_level_reader:
            return [
                base_case.clone(
                    # as a user with access reading right on inferior
                    # levels on a perimeter, I can see the accesses
                    # with readable roles on this perimeter's children
                    title=f"{right_group.name}-on inferior level-hosp2",
                    to_find=[a for a in right_group.readable_accesses
                             if a.perimeter_id == self.hospital3.id],
                    user_rights=[right_group.inf_level_reader],
                    user_perimeter=self.hospital2,
                ), base_case.clone(
                    # as a user with access reading right on inferior levels
                    # on a perimeter that has no children,
                    # I have no permission to read perimeters
                    title=f"{right_group.name}-on inferior levels-hosp3",
                    to_find=[],
                    user_rights=[right_group.inf_level_reader],
                    user_perimeter=self.hospital3,
                ), base_case.clone(
                    # as a user with access reading right on same level
                    # on a perimeter, I can see the accesses
                    # with readable roles on that perimeter
                    title=f"{right_group.name}-on same level-hosp2",
                    to_find=[a for a in right_group.readable_accesses
                             if a.perimeter_id == self.hospital2.id],
                    user_rights=[right_group.same_level_reader],
                    user_perimeter=self.hospital2,
                ), base_case.clone(
                    # as a user with access reading right on same level
                    # on a perimeter, I can see the accesses
                    # with readable roles on that perimeter
                    title=f"{right_group.name}-on same level-hosp3",
                    to_find=[a for a in right_group.readable_accesses
                             if a.perimeter_id == self.hospital3.id],
                    user_rights=[right_group.same_level_reader],
                    user_perimeter=self.hospital3,
                )]
        else:
            return [
                base_case.clone(
                    title=f"{right_group.name}-with {r}-hosp3",
                    to_find=right_group.readable_accesses.copy(),
                    user_rights=[r],
                    user_perimeter=self.hospital3,
                ) for r in right_group.rights]

    def test_get_accesses_simple_cases(self):
        def test_right_group(right_group: RightGroupForList):
            cases = self.prepare_right_group_list_case(right_group)
            for case in cases:
                self.check_get_acc_paged_list_case(case)
            [test_right_group(child) for child in right_group.children]

        test_right_group(self.right_groups_tree)

    def test_get_accesses_2_role_cases(self):
        def test_merged_right_group(right_group_a: RightGroupForList,
                                    right_group_b: RightGroupForList):
            # todo : problem is that total accesses to find will include
            #  accesses from wrong perimeter
            cases_a: List[AccessListCase] = self.prepare_right_group_list_case(
                right_group_a)
            cases_b: List[AccessListCase] = self.prepare_right_group_list_case(
                right_group_b)

            rights_for_full_access = list(set(sum([
                child.rights + (
                    any_manager_rights if child.is_manager_admin else []
                ) + child.all_children_rights()
                for child in right_group_a.children + right_group_b.children
            ], [])))

            for case_a, case_b in list(product(cases_a, cases_b)):
                case_a_perims = []

                if right_group_a.inf_level_reader:
                    if right_group_a.inf_level_reader in case_a.user_rights:
                        if case_a.user_perimeter.id == self.hospital2.id:
                            case_a_perims.append(self.hospital3)
                    if right_group_a.same_level_reader in case_a.user_rights:
                        case_a_perims.append(case_a.user_perimeter)
                else:
                    case_a_perims = [self.hospital2, self.hospital3]

                case_b_perims = []
                if right_group_b.inf_level_reader:
                    if right_group_b.inf_level_reader in case_b.user_rights:
                        if case_b.user_perimeter.id == self.hospital2.id:
                            case_b_perims.append(self.hospital3)
                    if right_group_b.same_level_reader in case_b.user_rights:
                        case_b_perims.append(case_b.user_perimeter)
                else:
                    case_b_perims = [self.hospital2, self.hospital3]

                new_case_perims = [p for p in case_a_perims
                                   if p in case_b_perims]

                new_full_accesses_to_add = create_accesses([
                    Role.objects.create(**dict(
                        [(f, True) for f in rights_for_full_access]
                        + [('name', f"{right_group_a} + {right_group_b}"
                                    f" - full")]
                    ))],
                    self.profiles_for_accesses, new_case_perims
                )

                accesses_to_add = new_full_accesses_to_add + [
                    acc for acc in
                    right_group_a.readable_accesses_with_other_rg(
                        right_group_b
                    ) if acc.perimeter_id in [p.id for p in new_case_perims]]

                # [set(
                #         case_a.accessible_perimeters_ids
                #     ).intersection(set(case_b.accessible_perimeters_ids))]]]

                self.check_get_paged_list_2_role_case(
                    case_a, case_b, accesses_to_add)
                [acc.delete() for acc in new_full_accesses_to_add]

        def list_right_groups(rg: RightGroup) -> List[RightGroup]:
            return [rg] + sum([list_right_groups(child)
                               for child in rg.children], [])

        list_right_groups = list_right_groups(self.right_groups_tree)
        [test_merged_right_group(rg_a, rg_b)
         for (rg_a, rg_b) in combinations(list_right_groups, 2)]

    def test_get_filtered_accesses_as_full_admin(self):
        # As a user with all the rights,
        # I can get accesses given query parameters
        user_full_admin, prof_full_admin = \
            new_user_and_profile()
        Access.objects.create(
            perimeter=self.aphp,
            profile=prof_full_admin,
            role=self.role_full,
        )
        base_result = [a for a in Access.objects.all()]

        # Adapt for search on perimeter_id
        # acc_with_hosp2 = [a for a in base_result
        #                   if a.perimeter_id == self.hospital2.id]
        # local_hosp2_id = 32220
        # self.hospital2.id = local_hosp2_id
        # self.hospital2.save()
        # for a in acc_with_hosp2:
        #     a.perimeter_id = local_hosp2_id
        # Access.objects.bulk_update(acc_with_hosp2, ['perimeter_id'])

        param_cases = {
            'search': [{
                'value': [
                    "NAME2",
                    # "222",
                    "FNaME2",
                    "lNaME2",
                    "maIL2",
                    self.user2_with_rnd_accesses.pk[-3:],
                ],
                'to_find': [a for a in base_result
                            if a.profile.id == self.prof2_with_rnd_accesses.id]
            }, {
                'value': self.hospital2.name,
                'to_find': [
                    a for a in base_result
                    if a.perimeter_id == self.hospital2.id
                ]
            }
            ],
            'perimeter': {
                'value': self.hospital2.id,
                'to_find': [a for a in base_result
                            if a.perimeter.id == self.hospital2.id]
            },
            'perimeter_name': {
                'value': "garden",
                'to_find': [
                    a for a in base_result if a.perimeter.id in [
                        perim.id for perim in self.all_perimeters
                        if "garden" in perim.name.lower()
                    ]
                ]
            },
            # 'target_perimeter_id': {
            #     'value': self.hospital2.id,
            #     'to_find': [
            #     ]
            # },
            'profile_id': {
                'value': self.prof2_with_rnd_accesses.id,
                'to_find': [
                    a for a in base_result
                    if a.profile.id == self.prof2_with_rnd_accesses.id
                ]
            },
            'profile_lastname': {
                'value': "Me1",
                'to_find': [a for a in base_result
                            if a.profile.id == self.prof_with_rnd_accesses.id]
            },
            'profile_firstname': {
                'value': "me1",
                'to_find': [a for a in base_result
                            if a.profile.id == self.prof_with_rnd_accesses.id]
            },
            'profile_email': {
                'value': "ail1",
                'to_find': [a for a in base_result
                            if a.profile.id == self.prof_with_rnd_accesses.id]
            },
            'profile_user_id': {
                'value': self.user_with_rnd_accesses.pk[-3:],
                'to_find': [a for a in base_result
                            if a.profile.id == self.prof_with_rnd_accesses.id]
            },
        }

        for (param, pc) in param_cases.items():
            pcs = [pc] if not isinstance(pc, list) else pc
            for pc_ in pcs:
                param_cases = [
                    {**pc_, 'value': v} for v in pc_['value']
                ] if isinstance(pc_['value'], list) else [pc_]

                [
                    self.check_get_acc_paged_list_case(ListCase(
                        title=f"{param}: {p_case['value']}",
                        params=dict({param: p_case['value']}),
                        to_find=p_case['to_find'],
                        user=user_full_admin,
                        status=http_status.HTTP_200_OK,
                        success=True,
                    )) for p_case in param_cases
                ]


class AccessDataRightsTests(ViewSetTestsWithBasicPerims):
    list_view = AccessViewSet.as_view({'get': 'data_rights'})
    objects_url = "/accesses/my-rights"

    def create_data_access(self, role: Role, perim: Perimeter) -> Access:
        return Access.objects.create(
            perimeter=perim,
            role=role,
            profile=self.profile1,
            start_datetime=timezone.now() - timedelta(days=1),
            end_datetime=timezone.now() + timedelta(days=2),
        )

    def basic_right_list_case(self, **kwargs) -> RightListCase:
        return RightListCase(
            **{**dict(success=True, status=http_status.HTTP_200_OK,
                      user=self.user1), **kwargs}
        )

    def setUp(self):
        super(AccessDataRightsTests, self).setUp()
        self.user1, self.profile1 = new_user_and_profile(
            p_name='user1', provider_id=2000000,
            firstname="Squall", lastname="Leonheart", email='s.l@aphp.fr'
        )
        self.full_data_read_role = Role.objects.create(
            name="full_data_read_role",
            right_read_patient_nominative=True,
            right_read_patient_pseudo_anonymised=True,
            right_search_patient_with_ipp=True,
        )
        self.pseudo_anonymised_data_role = Role.objects.create(
            name="PSEUDO_ANONYMISED_DATA_READER",
            right_read_patient_pseudo_anonymised=True,
        )
        self.nominative_data_role = Role.objects.create(
            name="NOMINATIVE_DATA_READER",
            right_read_patient_nominative=True,
        )
        self.search_ipp_role = Role.objects.create(
            name="SEARCH_IPP",
            right_search_patient_with_ipp=True,
        )
        self.pseudo_anonymised_export_role = Role.objects.create(
            name="PSEUDO_ANONYMISED_EXPORT_ROLE",
            right_export_csv_pseudo_anonymised=True,
        )
        self.nominative_export_role = Role.objects.create(
            name="NOMINATIVE_EXPORT_ROLE",
            right_export_csv_nominative=True,
        )
        self.base_aphp_right_dict = dict(
            right_read_patient_nominative=False,
            right_read_patient_pseudo_anonymised=False,
            right_search_patient_with_ipp=False,
            right_export_csv_nominative=False,
            right_export_csv_pseudo_anonymised=False,
            right_transfer_jupyter_nominative=False,
            right_transfer_jupyter_pseudo_anonymised=False,
            perimeter_id=str(self.aphp.id),
        )

    def check_get_list_case(self, case: RightListCase):
        request = self.factory.get(
            path=case.url or self.objects_url,
            data=[] if case.url else case.params)
        force_authenticate(request, case.user)
        response = self.__class__.list_view(request)
        response.render()
        self.assertEqual(
            response.status_code, case.status,
            msg=(f"{case.title}: "
                 + prettify_json(response.content) if response.content else ""),
        )

        res = json.loads(response.content)
        self.assertEqual(
            len(res), len(case.to_find),
            f"{case.description}; Found : {prettify_dict(res)}"
        )

        rights_found = []
        for r_f in res:
            try:
                rights_found.append(ReadRight(r_f))
            except Exception as e:
                self.fail(f"{case.description}: result has not-matching item "
                          f"{prettify_dict(r_f)} -> {e}")

        msg = case.description + "\n".join([
            "", "got", prettify_dict([r.__dict__ for r in rights_found]),
        ])
        # we check the equality of the case.to_find and teh rights_found
        for r_f in rights_found:
            if getattr(r_f, 'perimeter_id', None) is None:
                continue

            matching = [r for r in case.to_find if r.match(r_f)]
            self.assertEqual(len(matching), 1, msg)

    def test_get_top_rights_1(self):
        (access_pseudo_aphp, access_pseudo_hosp1, access_nomi_hosp3,
         access_ipp_hosp3) = [
            self.create_data_access(**d) for d in [
                dict(role=self.pseudo_anonymised_data_role,
                     perim=self.aphp),
                dict(role=self.pseudo_anonymised_data_role,
                     perim=self.hospital1),
                dict(role=self.nominative_data_role,
                     perim=self.hospital3),
                dict(role=self.search_ipp_role,
                     perim=self.hospital3),
            ]]
        case = self.basic_right_list_case(
            params={'pop_children': True},
            to_find=[ReadRight(d) for d in [
                {**self.base_aphp_right_dict,
                 'right_read_patient_pseudo_anonymised': True,
                 'access_ids': [access_pseudo_aphp.id]},
                {**self.base_aphp_right_dict,
                 'right_read_patient_nominative': True,
                 'right_search_patient_with_ipp': True,
                 'right_read_patient_pseudo_anonymised': True,
                 'access_ids': [access_nomi_hosp3.id, access_ipp_hosp3.id,
                                access_pseudo_aphp.id],
                 'perimeter_id': str(self.hospital3.id)}]],
            title='With pseudo on hosp1 and aphp, aphp dominates,'
                  ' also nomi and search_app on hosp3',
        )
        self.check_get_list_case(case)

    def test_get_top_rights_2(self):
        (access_pseudo_hosp1, access_ipp_hosp1, access_nomi_hosp3,
         access_nomi_aphp) = [
            self.create_data_access(**d) for d in [
                dict(role=self.pseudo_anonymised_data_role,
                     perim=self.hospital1),
                dict(role=self.search_ipp_role,
                     perim=self.hospital1),
                dict(role=self.nominative_data_role,
                     perim=self.hospital3),
                dict(role=self.nominative_data_role,
                     perim=self.aphp),
            ]]
        case = self.basic_right_list_case(
            params={'pop_children': True},
            to_find=[ReadRight(d) for d in [
                {**self.base_aphp_right_dict,
                 'access_ids': [access_nomi_aphp.id],
                 'right_read_patient_nominative': True},
                {**self.base_aphp_right_dict,
                 'right_search_patient_with_ipp': True,
                 'right_read_patient_nominative': True,
                 'right_read_patient_pseudo_anonymised': True,
                 'access_ids': [access_pseudo_hosp1.id, access_ipp_hosp1.id,
                                access_nomi_aphp.id],
                 'perimeter_id': str(self.hospital1.id)}]],
            title='With nomi on hosp3 and aphp, aphp dominates,'
                  'also pseudo and search_ipp on hosp1',
        )
        self.check_get_list_case(case)

    def test_get_top_rights_3(self):
        (access_pseudo_hosp1, access_nomi_hosp3, access_search_ipp,
         access_full_aphp) = [
            self.create_data_access(**d) for d in [
                dict(role=self.pseudo_anonymised_data_role,
                     perim=self.hospital1),
                dict(role=self.nominative_data_role,
                     perim=self.hospital3),
                dict(role=self.search_ipp_role,
                     perim=self.hospital2),
                dict(role=self.full_data_read_role,
                     perim=self.aphp),
            ]]
        case = self.basic_right_list_case(
            params={'pop_children': True},
            to_find=[ReadRight({
                **self.base_aphp_right_dict,
                'access_ids': [access_full_aphp.id],
                'right_read_patient_nominative': True,
                'right_read_patient_pseudo_anonymised': True,
                'right_search_patient_with_ipp': True,
            })],
            title='With pseudo on hosp1 and aphp, also nomi on hosp3 and aphp,'
                  'aphp dominates on both',
        )
        self.check_get_list_case(case)

    def test_get_rights_on_perimeters_1(self):
        #    ps
        # ps    nom
        #         exp_ps
        (access_pseudo_aphp, access_pseudo_hosp1, acc_ipp_hosp1,
         access_nomi_hosp2, access_exp_pseudo_hosp3) = [
            self.create_data_access(**d) for d in [
                dict(role=self.pseudo_anonymised_data_role,
                     perim=self.aphp),
                dict(role=self.pseudo_anonymised_data_role,
                     perim=self.hospital1),
                dict(role=self.search_ipp_role,
                     perim=self.hospital1),
                dict(role=self.nominative_data_role,
                     perim=self.hospital2),
                dict(role=self.pseudo_anonymised_export_role,
                     perim=self.hospital3),
            ]]
        case = self.basic_right_list_case(
            params={'perimeters_ids': ",".join([
                str(perim.id) for perim in [self.aphp, self.hospital1,
                                            self.hospital2, self.hospital3]
            ])},
            to_find=[ReadRight(d) for d in [
                {**self.base_aphp_right_dict,
                 'access_ids': [access_pseudo_aphp.id,
                                access_exp_pseudo_hosp3.id],
                 'right_read_patient_pseudo_anonymised': True,
                 'right_export_csv_pseudo_anonymised': True},
                {**self.base_aphp_right_dict,
                 'access_ids': [access_pseudo_aphp.id, access_pseudo_aphp.id,
                                access_exp_pseudo_hosp3.id, acc_ipp_hosp1.id],
                 'right_read_patient_pseudo_anonymised': True,
                 'right_search_patient_with_ipp': True,
                 'right_export_csv_pseudo_anonymised': True,
                 'perimeter_id': str(self.hospital1.id)},
                {**self.base_aphp_right_dict,
                 'access_ids': [access_pseudo_aphp.id, access_nomi_hosp2.id,
                                access_exp_pseudo_hosp3.id],
                 'right_read_patient_nominative': True,
                 'right_read_patient_pseudo_anonymised': True,
                 'right_export_csv_pseudo_anonymised': True,
                 'perimeter_id': str(self.hospital2.id)},
                {**self.base_aphp_right_dict,
                 'access_ids': [access_pseudo_aphp.id, access_nomi_hosp2.id,
                                access_exp_pseudo_hosp3.id],
                 'right_read_patient_nominative': True,
                 'right_read_patient_pseudo_anonymised': True,
                 'right_export_csv_pseudo_anonymised': True,
                 'perimeter_id': str(self.hospital3.id)},
            ]],
            title="With pseudo on hosp1 and aphp, aphp dominates,"
                  "also nomi on hosp2 and search_ipp on hosp1. "
                  "Pseudo export on hosp3 implies the right globally",
        )
        self.check_get_list_case(case)

    def test_get_rights_on_perimeters_2(self):
        (access_nomi_aphp, access_pseudo_hosp1, access_nomi_hosp2, acc_ipp,
         access_exp_nomi_hosp3) = [
            self.create_data_access(**d) for d in [
                dict(role=self.nominative_data_role,
                     perim=self.aphp),
                dict(role=self.pseudo_anonymised_data_role,
                     perim=self.hospital1),
                dict(role=self.nominative_data_role,
                     perim=self.hospital2),
                dict(role=self.search_ipp_role,
                     perim=self.hospital2),
                dict(role=self.nominative_export_role,
                     perim=self.hospital3),
            ]]

        case = self.basic_right_list_case(
            params={'perimeters_ids': ",".join([
                str(perim.id) for perim in [self.aphp, self.hospital1,
                                            self.hospital2, self.hospital3]
            ])},
            to_find=[ReadRight(d) for d in [
                {**self.base_aphp_right_dict,
                 'access_ids': [access_nomi_aphp.id, access_exp_nomi_hosp3.id],
                 'right_read_patient_nominative': True,
                 'right_export_csv_nominative': True},
                {**self.base_aphp_right_dict,
                 'access_ids': [access_nomi_aphp.id, access_exp_nomi_hosp3.id,
                                access_pseudo_hosp1.id],
                 'right_read_patient_nominative': True,
                 'right_read_patient_pseudo_anonymised': True,
                 'right_export_csv_nominative': True,
                 'perimeter_id': str(self.hospital1.id)},
                {**self.base_aphp_right_dict,
                 'access_ids': [access_nomi_aphp.id, access_exp_nomi_hosp3.id,
                                access_nomi_hosp2.id, acc_ipp.id],
                 'right_read_patient_nominative': True,
                 'right_search_patient_with_ipp': True,
                 'right_export_csv_nominative': True,
                 'perimeter_id': str(self.hospital2.id)},
                {**self.base_aphp_right_dict,
                 'access_ids': [access_nomi_aphp.id, access_exp_nomi_hosp3.id,
                                access_nomi_hosp2.id, acc_ipp.id],
                 'right_read_patient_nominative': True,
                 'right_search_patient_with_ipp': True,
                 'right_export_csv_nominative': True,
                 'perimeter_id': str(self.hospital3.id)},
            ]],
            title="With nomi on hosp2 and aphp, aphp dominates,also pseudo "
                  "on hosp1. Nominative export on hosp3 "
                  "implies the right globally",
        )
        self.check_get_list_case(case)

    def test_get_rights_on_perimeters_3(self):
        access_pseudo_hosp1, access_nomi_hosp2, access_full_aphp = [
            self.create_data_access(**d) for d in [
                dict(role=self.pseudo_anonymised_data_role,
                     perim=self.hospital1),
                dict(role=self.nominative_data_role,
                     perim=self.hospital2),
                dict(role=self.full_data_read_role,
                     perim=self.aphp),
            ]]
        case = self.basic_right_list_case(
            params={'perimeters_ids': ",".join([
                str(perim.id) for perim in [self.aphp, self.hospital1,
                                            self.hospital2, self.hospital3]
            ])},
            to_find=[ReadRight(d) for d in [
                {**self.base_aphp_right_dict,
                 'access_ids': [access_full_aphp.id],
                 'right_read_patient_nominative': True,
                 'right_search_patient_with_ipp': True,
                 'right_read_patient_pseudo_anonymised': True},
                {**self.base_aphp_right_dict,
                 'access_ids': [access_full_aphp.id, access_pseudo_hosp1.id],
                 'right_read_patient_nominative': True,
                 'right_read_patient_pseudo_anonymised': True,
                 'right_search_patient_with_ipp': True,
                 'perimeter_id': str(self.hospital1.id)},
                {**self.base_aphp_right_dict,
                 'access_ids': [access_full_aphp.id, access_nomi_hosp2.id],
                 'right_read_patient_nominative': True,
                 'right_read_patient_pseudo_anonymised': True,
                 'right_search_patient_with_ipp': True,
                 'perimeter_id': str(self.hospital2.id)},
                {**self.base_aphp_right_dict,
                 'access_ids': [access_full_aphp.id, access_nomi_hosp2.id],
                 'right_read_patient_nominative': True,
                 'right_read_patient_pseudo_anonymised': True,
                 'right_search_patient_with_ipp': True,
                 'perimeter_id': str(self.hospital3.id)}]],
            title='With pseudo on hosp1 and aphp, also nomi on hosp2 and aphp,'
                  'aphp dominates on both',
        )
        self.check_get_list_case(case)


class AccessMyAccessesTests(ViewSetTestsWithBasicPerims):
    list_view = AccessViewSet.as_view({'get': 'my_accesses'})
    objects_url = "/accesses/my-accesses"

    def create_data_access(self, role: Role, perim: Perimeter) -> Access:
        return Access.objects.create(
            perimeter=perim,
            role=role,
            profile=self.profile1,
            start_datetime=timezone.now() - timedelta(days=1),
            end_datetime=timezone.now() + timedelta(days=2),
        )

    def basic_right_list_case(self, **kwargs) -> RightListCase:
        return RightListCase(
            **{**dict(success=True, status=http_status.HTTP_200_OK,
                      user=self.user1), **kwargs}
        )

    def setUp(self):
        super(AccessMyAccessesTests, self).setUp()
        self.user1 = new_random_user(email='us@ser.1')
        self.user_empty = new_random_user(email='user@emp.ty')
        self.empty_role = Role.objects.create(name="empty")

        self.now = timezone.now()
        tomorrow = self.now + timedelta(days=1)
        yesterday = self.now - timedelta(days=1)
        next_week = self.now + timedelta(days=7)
        last_week = self.now - timedelta(days=7)

        end_dates = [None, next_week, yesterday]
        start_dates = [None, last_week, tomorrow]
        bools = [False, True]

        base_access = dict(role=self.empty_role, perimeter=self.aphp)
        user1_profiles = Profile.objects.bulk_create([Profile(
            user=self.user1,
            is_active=ia,
            manual_is_active=mia,
            valid_start_datetime=vsd,
            manual_valid_start_datetime=mvsd,
            valid_end_datetime=ved,
            manual_valid_end_datetime=mved,
            source=s,
        ) for (ia, mia, vsd, mvsd, ved, mved, s) in product(
            bools, bools, start_dates, start_dates, end_dates, end_dates,
            [MANUAL_SOURCE, "not_manual"]
        )])

        self.user1_accesses: List[Access] = Access.objects.bulk_create([
            Access(
                profile=prof, start_datetime=sd, end_datetime=ed,
                **base_access
            ) for (prof, sd, ed, msd, med) in product(
                user1_profiles, start_dates, end_dates, start_dates,
                end_dates
            )
        ])

    def check_get_list_case(self, case: ListCase):
        request = self.factory.get(
            path=case.url or self.objects_url,
            data=[] if case.url else case.params)
        force_authenticate(request, case.user)
        response = self.__class__.list_view(request)
        response.render()
        self.assertEqual(
            response.status_code, case.status,
            msg=(f"{case.title}: "
                 + prettify_json(response.content) if response.content else ""),
        )

        res = json.loads(response.content)

        acc_found = []
        for acc_f in res:
            try:
                acc_found.append(ReadAccess(acc_f))
            except Exception as e:
                self.fail(f"{case.description}: result has not-matching item "
                          f"{prettify_dict(acc_f)} -> {e}")

        found_ids = [acc_f.id for acc_f in acc_found]
        to_find_ids = [acc_tf.id for acc_tf in case.to_find]
        msg = case.description + "\n".join([
            "found but shouldn't be: ",
            prettify_dict([acc.__dict__ for acc in acc_found
                           if acc.id not in to_find_ids][0:10]),
            "not found but should be: ",
            prettify_dict([{**acc.__dict__, 'profile': acc.profile.__dict__}
                           for acc in case.to_find
                           if acc.id not in found_ids][0:10]),
        ])
        self.assertCountEqual(found_ids, to_find_ids, msg)

    def test_my_accesses(self):
        case = ListCase(
            user=self.user1, status=http_status.HTTP_200_OK,
            success=True, to_find=[
                a for a in self.user1_accesses
                if (a.is_valid and a.profile.is_valid
                    and a.profile.source == MANUAL_SOURCE)
            ])
        self.check_get_list_case(case)

    def test_my_accesses_empty(self):
        case = ListCase(
            user=self.user_empty, status=http_status.HTTP_200_OK,
            success=True, to_find=[])
        self.check_get_list_case(case)


# EVEN WITH SUPER ADMIN (all the rights on top perimeter)

class AccessAsSuperAdminTests(AccessTests):
    # As a user with all the rights on the top perimeter, ...
    def setUp(self):
        super(AccessAsSuperAdminTests, self).setUp()
        self.roles_any: List[Role] = [
            Role.objects.create(**{f: True}) for f in ALL_RIGHTS
        ]

        self.user_with_rights, self.prof_with_rights = new_user_and_profile(
            email='with@rights.com')

        Access.objects.create(
            perimeter=self.aphp,
            profile=self.prof_with_rights,
            role=self.role_full,
        )

        self.user_with_nothing, self.prof_with_nothing = new_user_and_profile(
            email='no@thing.com')
        self.user2_with_nothing, self.ph2_with_nothing = new_user_and_profile(
            email='no2@thing.com')

    def test_err_delete_any_started_access_even_as_full_admin(self):
        # ... I cannot delete an access whom the start_datetime has passed
        cases = [DeleteCase(
            data_to_delete=dict(
                perimeter=perim,
                role=r,
                profile=self.prof_with_nothing,
                start_datetime=timezone.now() - timedelta(days=1),
            ),
            success=False,
            user=self.user_with_rights,
            status=http_status.HTTP_403_FORBIDDEN,
        ) for (perim, r) in product([self.aphp, self.hospital2,
                                     self.hospital3], self.roles_any)
        ]

        [self.check_delete_case(case) for case in cases]

    def test_err_patch_passed_datetime_even_as_full_admin(self):
        # ... I cannot update any datetime of an access
        # if that datetime is passed
        cases = [PatchCase(
            initial_data=dict(
                perimeter=perim,
                role=r,
                profile=self.prof_with_nothing,
                start_datetime=timezone.now() - timedelta(days=1),
                end_datetime=timezone.now() + timedelta(days=2),
            ),
            data_to_update=dict(
                start_datetime=timezone.now() + timedelta(days=2),
            ),
            success=False,
            user=self.user_with_rights,
            status=http_status.HTTP_400_BAD_REQUEST,
        ) for (perim, r) in product(
            [self.hospital2, self.aphp, self.hospital3], self.roles_any
        )] + [PatchCase(
            initial_data=dict(
                perimeter=perim,
                role=r,
                profile=self.prof_with_nothing,
                start_datetime=timezone.now() + timedelta(days=1),
                end_datetime=timezone.now() - timedelta(days=2),
            ),
            data_to_update=dict(
                end_datetime=timezone.now() + timedelta(days=2),
            ),
            success=False,
            user=self.user_with_rights,
            status=http_status.HTTP_400_BAD_REQUEST,
        ) for (perim, r) in product(
            [self.hospital2, self.aphp, self.hospital3], self.roles_any
        )]

        [self.check_patch_case(case) for case in cases]

    def test_err_patch_wrong_field_even_as_full_admin(self):
        # ... I cannot update any other field than datetimes of an access
        examples = dict(
            id=999999,
            perimeter_id=self.hospital3.id,
            profile=self.ph2_with_nothing.id,
            role=self.role_empty.id,
            source='oui',
            start_datetime=timezone.now() + timedelta(days=1),
            end_datetime=timezone.now() + timedelta(days=2),
        )

        cases = [PatchCase(
            initial_data=dict(
                perimeter=self.hospital2,
                role=r,
                profile=self.prof_with_nothing,
                start_datetime=timezone.now() + timedelta(days=1),
                end_datetime=timezone.now() + timedelta(days=2),
            ),
            data_to_update=to_update,
            success=False,
            user=self.user_with_rights,
            status=http_status.HTTP_200_OK,
        ) for (to_update, r) in product(
            [dict([(k, v)]) for (k, v) in examples.items()]
            + [dict(role=r.id) for r in self.roles_any],
            self.roles_any
        )]

        [self.check_patch_case(case) for case in cases]

    def test_err_close_passed_end_datetime_even_as_full_admin(self):
        # ... I cannot close an access whom end_datetime has passed
        cases = [AccessCloseCase(
            initial_data=dict(
                perimeter=perim,
                role=r,
                profile=self.prof_with_nothing,
                start_datetime=timezone.now() - timedelta(days=2),
                end_datetime=timezone.now() - timedelta(days=1),
            ),
            success=False,
            user=self.user_with_rights,
            status=http_status.HTTP_403_FORBIDDEN,
        ) for (perim, r) in product(
            [self.hospital2, self.aphp, self.hospital3], self.roles_any
        )]

        [self.check_close_case(case) for case in cases]

    def test_err_close_not_passed_start_datetime_even_as_full_admin(self):
        # ... I cannot close an access whom start_datetime has not passed
        cases = [AccessCloseCase(
            initial_data=dict(
                perimeter=perim,
                role=r,
                profile=self.prof_with_nothing,
                start_datetime=timezone.now() + timedelta(days=1),
                end_datetime=timezone.now() + timedelta(days=2),
            ),
            success=False,
            user=self.user_with_rights,
            status=http_status.HTTP_403_FORBIDDEN,
        ) for (perim, r) in product(
            [self.hospital2, self.aphp, self.hospital3], self.roles_any
        )]

        [self.check_close_case(case) for case in cases]


class AccessAsEachAdminTests(AccessTests):
    def setUp(self):
        super(AccessAsEachAdminTests, self).setUp()
        self.right_groups_tree: RightGroupForManage = \
            RightGroupForManage.clone_from_right_group(RIGHT_GROUPS)

        self.user_with_nothing, self.prof_with_nothing = new_user_and_profile()

        def add_roles_to_right_groups_tree(
                rg: RightGroupForManage, parent: RightGroupForManage = None
        ):
            rg.full_role = Role.objects.create(
                **dict([
                    (f, True) for f in
                    rg.rights
                    + (any_manager_rights if rg.is_manager_admin else [])
                ]))
            rg.full_role_with_any_from_child = [
                Role.objects.create(
                    **dict([
                        (f, True) for f in
                        rg.rights
                        + (any_manager_rights if rg.is_manager_admin else [])
                        + [right]
                    ])) for right in rg.all_children_rights()
                if right not in rg.all_children_rights(r=True)
            ]
            rg.full_role_with_any_from_direct_child = [
                Role.objects.create(
                    **dict([
                        (f, True) for f in
                        rg.rights
                        + (any_manager_rights if rg.is_manager_admin else [])
                        + [right]
                    ])) for right in rg.all_children_rights(r=False)
            ]

            if parent:
                rg.siblings_rights = parent.all_children_rights(
                    r=False, exempt=rg.name)
                rg.full_role_with_any_from_siblings = [
                    Role.objects.create(
                        **dict([(f, True) for f in
                                rg.rights + [right]
                                + (any_manager_rights
                                   if rg.is_manager_admin else [])
                                ])) for right in rg.siblings_rights
                ]
                rg.full_role_with_any_from_parent = [
                    Role.objects.create(
                        **dict([(f, True) for f in rg.rights + [right]
                                + (any_manager_rights
                                   if rg.is_manager_admin else [])
                                ])) for right in parent.rights
                    if right not in rg.rights
                ]

            for child in rg.children:
                add_roles_to_right_groups_tree(child, rg)

        add_roles_to_right_groups_tree(self.right_groups_tree)


class AccessCreateAsEachAdminTests(AccessAsEachAdminTests):
    def setUp(self):
        super(AccessCreateAsEachAdminTests, self).setUp()
        self.simple_create_case = AccessCreateCase(
            user=self.user1,
            user_profile=self.profile1,
            success=True,
            user_perimeter=self.hospital2,
            status=http_status.HTTP_201_CREATED,
            data=dict(), user_role=None,
        )
        self.simple_err_create_case = self.simple_create_case.clone(
            success=False, status=http_status.HTTP_403_FORBIDDEN)

    def test_create_access_as_admin(self):
        def test_rights_group(rg: RightGroupForManage):
            if rg.same_level_editor and rg.inf_level_editor:
                cases = sum([[self.simple_create_case.clone(
                    title=f"{rg.name}-on same level-hosp2-{role.help_text}",
                    user_rights=[rg.same_level_editor],
                    data=dict(
                        perimeter_id=self.hospital2.id,
                        role_id=role.id,
                        profile_id=self.prof_with_nothing.id
                    ),
                ), self.simple_create_case.clone(
                    title=f"{rg.name}-on inferiors levels-hosp3"
                          f"-{role.help_text}",
                    user_rights=[rg.inf_level_editor],
                    data=dict(
                        perimeter_id=self.hospital3.id,
                        role_id=role.id,
                        profile_id=self.prof_with_nothing.id
                    ),
                )] for role in rg.manageable_roles], [])
            else:
                cases = [self.simple_create_case.clone(
                    title=f"{rg.name}-with {right}-{perim.name}"
                          f"-{role.help_text}",
                    user_rights=[right],
                    data=dict(
                        perimeter_id=perim.id,
                        role_id=role.id,
                        profile_id=self.prof_with_nothing.id
                    )) for (perim, role, right) in product(
                    [self.hospital1, self.aphp, self.hospital2, self.hospital3],
                    rg.manageable_roles, rg.rights)
                ]

            [self.check_create_case(case) for case in cases]
            for child in rg.children:
                test_rights_group(child)

        test_rights_group(self.right_groups_tree)

    def test_error_create_access_without_right(self):
        def test_rights_group(rg: RightGroupForManage):
            if rg.same_level_editor and rg.inf_level_editor:
                cases = sum([[self.simple_err_create_case.clone(
                    title=f"{rg.name}-on same level-hosp2-{role.help_text}",
                    user_rights=[rg.same_level_editor],
                    data=dict(
                        perimeter_id=self.hospital2.id,
                        role_id=role.id,
                        profile_id=self.prof_with_nothing.id
                    ),
                ), self.simple_err_create_case.clone(
                    title=f"{rg.name}-on inferior levels-hosp3"
                          f"-{role.help_text}",
                    user_rights=[rg.inf_level_editor],
                    data=dict(
                        perimeter_id=self.hospital3.id,
                        role_id=role.id,
                        profile_id=self.prof_with_nothing.id
                    ),
                )] for role in rg.unmanageable_roles], [])
            else:
                cases = [self.simple_err_create_case.clone(
                    title=f"{rg.name}-with {right}-{perim.name}"
                          f"-{role.help_text}",
                    user_rights=[right],
                    data=dict(
                        perimeter_id=perim.id,
                        role_id=role.id,
                        profile_id=self.prof_with_nothing.id
                    )) for (perim, role, right) in product(
                    [self.hospital1, self.aphp, self.hospital2, self.hospital3],
                    rg.unmanageable_roles, rg.rights)
                ]

            [self.check_create_case(case) for case in cases]
            for child in rg.children:
                test_rights_group(child)

        test_rights_group(self.right_groups_tree)

    def test_err_create_access_as_admin_wrong_perim(self):
        def test_rights_group(rg: RightGroupForManage):
            if rg.same_level_editor and rg.inf_level_editor:
                cases = sum([[self.simple_err_create_case.clone(
                    title=f"{rg.name}-on same level-hosp3-{role.help_text}",
                    user_rights=[rg.same_level_editor],
                    data=dict(
                        perimeter_id=self.hospital3.id,
                        role_id=role.id,
                        profile_id=self.prof_with_nothing.id
                    ),
                ), self.simple_err_create_case.clone(
                    title=f"{rg.name}-on same level-aphp-{role.help_text}",
                    user_rights=[rg.same_level_editor],
                    data=dict(
                        perimeter_id=self.aphp.id,
                        role_id=role.id,
                        profile_id=self.prof_with_nothing.id
                    ),
                ), self.simple_err_create_case.clone(
                    title=f"{rg.name}-on inferior levels-hosp2"
                          f"-{role.help_text}",
                    user_rights=[rg.inf_level_editor],
                    data=dict(
                        perimeter_id=self.hospital2.id,
                        role_id=role.id,
                        profile_id=self.prof_with_nothing.id
                    ),
                )] for role in rg.manageable_roles], [])

                [self.check_create_case(case) for case in cases]
            for child in rg.children:
                test_rights_group(child)

        test_rights_group(self.right_groups_tree)


class AccessDeleteAsEachAdminTests(AccessAsEachAdminTests):
    def setUp(self):
        super(AccessDeleteAsEachAdminTests, self).setUp()
        self.simple_delete_case = AccessDeleteCase(
            user=self.user1,
            user_profile=self.profile1,
            user_perimeter=self.hospital2,
            success=True,
            status=http_status.HTTP_204_NO_CONTENT,
            data_to_delete=dict(), user_role=None,
        )
        self.simple_err_delete_case = self.simple_delete_case.clone(
            success=False, status=http_status.HTTP_403_FORBIDDEN)
        self.simple_unf_delete_case = self.simple_err_delete_case.clone(
            status=http_status.HTTP_404_NOT_FOUND)

    def prepare_initial_data(self, role=None, start_datetime=None,
                             end_datetime=None, perimeter=None,
                             profile=None) -> dict:
        return dict(
            start_datetime=start_datetime or (timezone.now()
                                              + timedelta(days=1)),
            end_datetime=end_datetime or (timezone.now() + timedelta(days=2)),
            perimeter=perimeter if perimeter is not None
            else self.hospital2.id,
            role=role,
            profile=profile or self.prof_with_nothing
        )

    def test_delete_access_as_admin(self):
        def test_rights_group(rg: RightGroupForManage):
            if rg.same_level_editor and rg.inf_level_editor:
                cases = sum([[self.simple_delete_case.clone(
                    title=f"{rg.name}-on same level-hosp2-{role.help_text}",
                    user_rights=[rg.same_level_editor, rg.same_level_reader],
                    data_to_delete=self.prepare_initial_data(
                        perimeter=self.hospital2,
                        role=role,
                    ),
                ), self.simple_delete_case.clone(
                    title=f"{rg.name}-on inf levels-hosp3-{role.help_text}",
                    user_rights=[rg.inf_level_editor, rg.inf_level_reader],
                    data_to_delete=self.prepare_initial_data(
                        perimeter=self.hospital3,
                        role=role,
                    ),
                )] for role in rg.manageable_roles], [])
            else:
                cases = [self.simple_delete_case.clone(
                    title=f"{rg.name}-with {right}-{perim.name}"
                          f"-{role.help_text}",
                    user_rights=[right],
                    data_to_delete=self.prepare_initial_data(
                        perimeter=perim,
                        role=role,
                    )) for (perim, role, right) in product(
                    [self.hospital1, self.aphp, self.hospital2, self.hospital3],
                    rg.manageable_roles, rg.rights)
                ]

            [self.check_delete_case(case) for case in cases]
            for child in rg.children:
                test_rights_group(child)

        test_rights_group(self.right_groups_tree)

    def test_error_delete_access_without_right(self):
        def test_rights_group(rg: RightGroupForManage):
            if rg.same_level_editor and rg.inf_level_editor:
                cases = sum([[self.simple_err_delete_case.clone(
                    title=f"{rg.name}-on same level-hosp2-{role.help_text}",
                    user_rights=[rg.same_level_editor, rg.same_level_reader],
                    status=http_status.HTTP_404_NOT_FOUND
                    if role in rg.unreadable_roles
                    else http_status.HTTP_403_FORBIDDEN,
                    data_to_delete=self.prepare_initial_data(
                        perimeter=self.hospital2,
                        role=role,
                    ),
                ), self.simple_err_delete_case.clone(
                    title=f"{rg.name}-on inf levels-hosp3-{role.help_text}",
                    user_rights=[rg.inf_level_editor, rg.inf_level_reader],
                    status=http_status.HTTP_404_NOT_FOUND
                    if role in rg.unreadable_roles
                    else http_status.HTTP_403_FORBIDDEN,
                    data_to_delete=self.prepare_initial_data(
                        perimeter=self.hospital3,
                        role=role,
                    ),
                )] for role in rg.unmanageable_roles], [])
            else:
                cases = [self.simple_err_delete_case.clone(
                    title=f"{rg.name}-with {right}-{perim.name}"
                          f"-{role.help_text}",
                    user_rights=[right],
                    status=http_status.HTTP_404_NOT_FOUND
                    if role in rg.unreadable_roles
                    else http_status.HTTP_403_FORBIDDEN,
                    data_to_delete=self.prepare_initial_data(
                        perimeter=perim,
                        role=role,
                    )) for (perim, role, right) in product(
                    [self.hospital2, self.hospital3],
                    rg.unmanageable_roles, rg.rights)
                ]

            [self.check_delete_case(case) for case in cases]
            for child in rg.children:
                test_rights_group(child)

        test_rights_group(self.right_groups_tree)

    def test_err_delete_access_as_admin_wrong_perim(self):
        def test_rights_group(rg: RightGroupForManage):
            if rg.same_level_editor and rg.inf_level_editor:
                cases = sum([[self.simple_err_delete_case.clone(
                    title=f"{rg.name}-on same level-hosp3-{role.help_text}",
                    user_rights=[rg.same_level_editor, rg.inf_level_reader],
                    data_to_delete=self.prepare_initial_data(
                        perimeter=self.hospital3,
                        role=role,
                    ),
                ), self.simple_err_delete_case.clone(
                    title=f"{rg.name}-on inf levels-hosp2-{role.help_text}",
                    user_rights=[rg.inf_level_editor, rg.same_level_reader],
                    data_to_delete=self.prepare_initial_data(
                        perimeter=self.hospital2,
                        role=role,
                    ),
                )] for role in rg.manageable_roles], [])

                [self.check_delete_case(case) for case in cases]
            for child in rg.children:
                test_rights_group(child)

        test_rights_group(self.right_groups_tree)

    def test_err_unfound_delete_access_as_admin_wrong_perim(self):
        def test_rights_group(rg: RightGroupForManage):
            if rg.same_level_editor and rg.inf_level_editor:
                cases = sum([[self.simple_unf_delete_case.clone(
                    title=f"{rg.name}-on same level-hosp3-{role.help_text}",
                    user_rights=[rg.same_level_editor, rg.same_level_reader],
                    data_to_delete=self.prepare_initial_data(
                        perimeter=self.hospital3,
                        role=role,
                    ),
                ), self.simple_unf_delete_case.clone(
                    title=f"{rg.name}-edit same/read same-aphp"
                          f"-{role.help_text}",
                    user_rights=[rg.same_level_editor, rg.same_level_reader],
                    data_to_delete=self.prepare_initial_data(
                        perimeter=self.aphp,
                        role=role,
                    ),
                ), self.simple_unf_delete_case.clone(
                    title=f"{rg.name}-edit same/read inf-aphp-{role.help_text}",
                    user_rights=[rg.same_level_editor, rg.inf_level_reader],
                    data_to_delete=self.prepare_initial_data(
                        perimeter=self.aphp,
                        role=role,
                    ),
                ), self.simple_unf_delete_case.clone(
                    title=f"{rg.name}-edit same/read inf-hosp2"
                          f"-{role.help_text}",
                    user_rights=[rg.same_level_editor, rg.inf_level_reader],
                    data_to_delete=self.prepare_initial_data(
                        perimeter=self.hospital2,
                        role=role,
                    ),
                ), self.simple_unf_delete_case.clone(
                    title=f"{rg.name}-edit inf/read same"
                          f"-hosp3-{role.help_text}",
                    user_rights=[rg.inf_level_editor, rg.same_level_reader],
                    data_to_delete=self.prepare_initial_data(
                        perimeter=self.hospital3,
                        role=role,
                    ),
                ), self.simple_unf_delete_case.clone(
                    title=f"{rg.name}-edit inf/read same-aphp-{role.help_text}",
                    user_rights=[rg.inf_level_editor, rg.same_level_reader],
                    data_to_delete=self.prepare_initial_data(
                        perimeter=self.aphp,
                        role=role,
                    ),
                ), self.simple_unf_delete_case.clone(
                    title=f"{rg.name}-on inf levels-hosp2-{role.help_text}",
                    user_rights=[rg.inf_level_editor, rg.inf_level_reader],
                    data_to_delete=self.prepare_initial_data(
                        perimeter=self.hospital2,
                        role=role,
                    ),
                ), self.simple_unf_delete_case.clone(
                    title=f"{rg.name}-on inf levels-aphp-{role.help_text}",
                    user_rights=[rg.inf_level_editor, rg.inf_level_reader],
                    data_to_delete=self.prepare_initial_data(
                        perimeter=self.aphp,
                        role=role,
                    ),
                )] for role in rg.manageable_roles], [])

                [self.check_delete_case(case) for case in cases]
            for child in rg.children:
                test_rights_group(child)

        test_rights_group(self.right_groups_tree)


class AccessPatchAsEachAdminTests(AccessAsEachAdminTests):
    def setUp(self):
        super(AccessPatchAsEachAdminTests, self).setUp()
        self.simple_patch_case = AccessPatchCase(
            user=self.user1,
            user_profile=self.profile1,
            user_perimeter=self.hospital2,
            success=True,
            status=http_status.HTTP_200_OK,
            initial_data=dict(), user_role=None,
            data_to_update=dict(end_datetime=timezone.now() + timedelta(days=1))
        )
        self.simple_err_patch_case = self.simple_patch_case.clone(
            success=False, status=http_status.HTTP_403_FORBIDDEN)
        self.simple_unf_patch_case = self.simple_err_patch_case.clone(
            status=http_status.HTTP_404_NOT_FOUND)

    def prepare_initial_data(self, role: Role = None,
                             start_datetime: datetime.datetime = None,
                             end_datetime: datetime.datetime = None,
                             perimeter: Perimeter = None,
                             profile: Profile = None):
        return dict(
            start_datetime=start_datetime or (timezone.now()
                                              + timedelta(days=1)),
            end_datetime=end_datetime or (timezone.now() + timedelta(days=2)),
            perimeter=perimeter if perimeter is not None
            else self.hospital2.id,
            role=role,
            profile=profile or self.prof_with_nothing
        )

    def test_patch_access_as_admin(self):
        def test_rights_group(rg: RightGroupForManage):
            if rg.same_level_editor and rg.inf_level_editor:
                cases = sum([[self.simple_patch_case.clone(
                    title=f"{rg.name}-on same level-hosp2-{role.help_text}",
                    user_rights=[rg.same_level_editor, rg.same_level_reader],
                    initial_data=self.prepare_initial_data(
                        perimeter=self.hospital2,
                        role=role,
                    ),
                ), self.simple_patch_case.clone(
                    title=f"{rg.name}-on inf levels-hosp3-{role.help_text}",
                    user_rights=[rg.inf_level_editor, rg.inf_level_reader],
                    initial_data=self.prepare_initial_data(
                        perimeter=self.hospital3,
                        role=role,
                    ),
                )] for role in rg.manageable_roles], [])
            else:
                cases = [self.simple_patch_case.clone(
                    title=f"{rg.name}-with {right}-{perim.name}"
                          f"-{role.help_text}",
                    user_rights=[right],
                    initial_data=self.prepare_initial_data(
                        perimeter=perim,
                        role=role,
                    )) for (perim, role, right) in product(
                    [self.hospital1, self.aphp, self.hospital2, self.hospital3],
                    rg.manageable_roles, rg.rights)
                ]

            [self.check_patch_case(case) for case in cases]
            for child in rg.children:
                test_rights_group(child)

        test_rights_group(self.right_groups_tree)

    def test_error_patch_access_without_right(self):
        def test_rights_group(rg: RightGroupForManage):
            if rg.same_level_editor and rg.inf_level_editor:
                cases = sum([[self.simple_err_patch_case.clone(
                    title=f"{rg.name}-on same level-hosp2-{role.help_text}",
                    user_rights=[rg.same_level_editor, rg.same_level_reader],
                    status=http_status.HTTP_404_NOT_FOUND
                    if role in rg.unreadable_roles
                    else http_status.HTTP_403_FORBIDDEN,
                    initial_data=self.prepare_initial_data(
                        perimeter=self.hospital2,
                        role=role,
                    ),
                ), self.simple_err_patch_case.clone(
                    title=f"{rg.name}-on inf levels-hosp3-{role.help_text}",
                    user_rights=[rg.inf_level_editor, rg.inf_level_reader],
                    status=http_status.HTTP_404_NOT_FOUND
                    if role in rg.unreadable_roles
                    else http_status.HTTP_403_FORBIDDEN,
                    initial_data=self.prepare_initial_data(
                        perimeter=self.hospital3,
                        role=role,
                    ),
                )] for role in rg.unmanageable_roles], [])
            else:
                cases = [self.simple_err_patch_case.clone(
                    title=f"{rg.name}-with {right}-{perim.name}"
                          f"-{role.help_text}",
                    user_rights=[right],
                    status=http_status.HTTP_404_NOT_FOUND
                    if role in rg.unreadable_roles
                    else http_status.HTTP_403_FORBIDDEN,
                    initial_data=self.prepare_initial_data(
                        perimeter=perim,
                        role=role,
                    )) for (perim, role, right) in product(
                    [self.hospital2, self.hospital3],
                    rg.unmanageable_roles, rg.rights)
                ]

            [self.check_patch_case(case) for case in cases]
            for child in rg.children:
                test_rights_group(child)

        test_rights_group(self.right_groups_tree)

    def test_err_patch_access_as_admin_wrong_perim(self):
        def test_rights_group(rg: RightGroupForManage):
            if rg.same_level_editor and rg.inf_level_editor:
                cases = sum([[self.simple_err_patch_case.clone(
                    title=f"{rg.name}-on same level-hosp3-{role.help_text}",
                    user_rights=[rg.same_level_editor, rg.inf_level_reader],
                    initial_data=self.prepare_initial_data(
                        perimeter=self.hospital3,
                        role=role,
                    ),
                ), self.simple_err_patch_case.clone(
                    title=f"{rg.name}-on inf levels-hosp2-{role.help_text}",
                    user_rights=[rg.inf_level_editor, rg.same_level_reader],
                    initial_data=self.prepare_initial_data(
                        perimeter=self.hospital2,
                        role=role,
                    ),
                )] for role in rg.manageable_roles], [])

                [self.check_patch_case(case) for case in cases]
            for child in rg.children:
                test_rights_group(child)

        test_rights_group(self.right_groups_tree)

    def test_err_unfound_patch_access_as_admin_wrong_perim(self):
        def test_rights_group(rg: RightGroupForManage):
            if rg.same_level_editor and rg.inf_level_editor:
                cases = sum([[self.simple_unf_patch_case.clone(
                    title=f"{rg.name}-on same level-hosp3-{role.help_text}",
                    user_rights=[rg.same_level_editor, rg.same_level_reader],
                    initial_data=self.prepare_initial_data(
                        perimeter=self.hospital3,
                        role=role,
                    ),
                ), self.simple_unf_patch_case.clone(
                    title=f"{rg.name}-edit same/read same-aphp"
                          f"-{role.help_text}",
                    user_rights=[rg.same_level_editor, rg.same_level_reader],
                    initial_data=self.prepare_initial_data(
                        perimeter=self.aphp,
                        role=role,
                    ),
                ), self.simple_unf_patch_case.clone(
                    title=f"{rg.name}-edit same/read inf-aphp-{role.help_text}",
                    user_rights=[rg.same_level_editor, rg.inf_level_reader],
                    initial_data=self.prepare_initial_data(
                        perimeter=self.aphp,
                        role=role,
                    ),
                ), self.simple_unf_patch_case.clone(
                    title=f"{rg.name}-edit same/read inf-hosp2"
                          f"-{role.help_text}",
                    user_rights=[rg.same_level_editor, rg.inf_level_reader],
                    initial_data=self.prepare_initial_data(
                        perimeter=self.hospital2,
                        role=role,
                    ),
                ), self.simple_unf_patch_case.clone(
                    title=f"{rg.name}-edit inf/read same"
                          f"-hosp3-{role.help_text}",
                    user_rights=[rg.inf_level_editor, rg.same_level_reader],
                    initial_data=self.prepare_initial_data(
                        perimeter=self.hospital3,
                        role=role,
                    ),
                ), self.simple_unf_patch_case.clone(
                    title=f"{rg.name}-edit inf/read same-aphp-{role.help_text}",
                    user_rights=[rg.inf_level_editor, rg.same_level_reader],
                    initial_data=self.prepare_initial_data(
                        perimeter=self.aphp,
                        role=role,
                    ),
                ), self.simple_unf_patch_case.clone(
                    title=f"{rg.name}-on inf levels-hosp2-{role.help_text}",
                    user_rights=[rg.inf_level_editor, rg.inf_level_reader],
                    initial_data=self.prepare_initial_data(
                        perimeter=self.hospital2,
                        role=role,
                    ),
                ), self.simple_unf_patch_case.clone(
                    title=f"{rg.name}-on inf levels-aphp-{role.help_text}",
                    user_rights=[rg.inf_level_editor, rg.inf_level_reader],
                    initial_data=self.prepare_initial_data(
                        perimeter=self.aphp,
                        role=role,
                    ),
                )] for role in rg.manageable_roles], [])

                [self.check_patch_case(case) for case in cases]
            for child in rg.children:
                test_rights_group(child)

        test_rights_group(self.right_groups_tree)


class AccessCloseAsEachAdminTests(AccessAsEachAdminTests):
    def setUp(self):
        super(AccessCloseAsEachAdminTests, self).setUp()
        self.simple_close_case = AccessCloseCase(
            user=self.user1,
            user_profile=self.profile1,
            user_perimeter=self.hospital2,
            success=True,
            status=http_status.HTTP_200_OK,
            initial_data=dict(), user_role=None,
        )
        self.simple_err_close_case = self.simple_close_case.clone(
            success=False, status=http_status.HTTP_403_FORBIDDEN)
        self.simple_unf_close_case = self.simple_err_close_case.clone(
            status=http_status.HTTP_404_NOT_FOUND)

    def prepare_initial_data(self, role: Role = None,
                             start_datetime: datetime.datetime = None,
                             end_datetime: datetime.datetime = None,
                             perimeter: Perimeter = None,
                             profile: Profile = None):
        return dict(
            start_datetime=start_datetime or (timezone.now()
                                              - timedelta(days=1)),
            end_datetime=end_datetime or (timezone.now() + timedelta(days=2)),
            perimeter=perimeter if perimeter is not None
            else self.hospital2.id,
            role=role,
            profile=profile or self.prof_with_nothing
        )

    def test_close_access_as_admin(self):
        def test_rights_group(rg: RightGroupForManage):
            if rg.same_level_editor and rg.inf_level_editor:
                cases = sum([[self.simple_close_case.clone(
                    title=f"{rg.name}-on same level-hosp2-{role.help_text}",
                    user_rights=[rg.same_level_editor, rg.same_level_reader],
                    initial_data=self.prepare_initial_data(
                        perimeter=self.hospital2,
                        role=role,
                    ),
                ), self.simple_close_case.clone(
                    title=f"{rg.name}-on inf levels-hosp3-{role.help_text}",
                    user_rights=[rg.inf_level_editor, rg.inf_level_reader],
                    initial_data=self.prepare_initial_data(
                        perimeter=self.hospital3,
                        role=role,
                    ),
                )] for role in rg.manageable_roles], [])
            else:
                cases = [self.simple_close_case.clone(
                    title=f"{rg.name}-with {right}-{perim.name}"
                          f"-{role.help_text}",
                    user_rights=[right],
                    initial_data=self.prepare_initial_data(
                        perimeter=perim,
                        role=role,
                    )) for (perim, role, right) in product(
                    [self.hospital1, self.aphp, self.hospital2, self.hospital3],
                    rg.manageable_roles, rg.rights)
                ]

            [self.check_close_case(case) for case in cases]
            for child in rg.children:
                test_rights_group(child)

        test_rights_group(self.right_groups_tree)

    def test_error_close_access_without_right(self):
        def test_rights_group(rg: RightGroupForManage):
            if rg.same_level_editor and rg.inf_level_editor:
                cases = sum([[self.simple_err_close_case.clone(
                    title=f"{rg.name}-on same level-hosp2-{role.help_text}",
                    user_rights=[rg.same_level_editor, rg.same_level_reader],
                    status=http_status.HTTP_404_NOT_FOUND
                    if role in rg.unreadable_roles
                    else http_status.HTTP_403_FORBIDDEN,
                    initial_data=self.prepare_initial_data(
                        perimeter=self.hospital2,
                        role=role,
                    ),
                ), self.simple_err_close_case.clone(
                    title=f"{rg.name}-on inf levels-hosp3-{role.help_text}",
                    user_rights=[rg.inf_level_editor, rg.inf_level_reader],
                    status=http_status.HTTP_404_NOT_FOUND
                    if role in rg.unreadable_roles
                    else http_status.HTTP_403_FORBIDDEN,
                    initial_data=self.prepare_initial_data(
                        perimeter=self.hospital3,
                        role=role,
                    ),
                )] for role in rg.unmanageable_roles], [])
            else:
                cases = [self.simple_err_close_case.clone(
                    title=f"{rg.name}-with {right}-{perim.name}"
                          f"-{role.help_text}",
                    user_rights=[right],
                    status=http_status.HTTP_404_NOT_FOUND
                    if role in rg.unreadable_roles
                    else http_status.HTTP_403_FORBIDDEN,
                    initial_data=self.prepare_initial_data(
                        perimeter=perim,
                        role=role,
                    )) for (perim, role, right) in product(
                    [self.hospital2, self.hospital3],
                    rg.unmanageable_roles, rg.rights)
                ]

            [self.check_close_case(case) for case in cases]
            for child in rg.children:
                test_rights_group(child)

        test_rights_group(self.right_groups_tree)

    def test_err_close_access_as_admin_wrong_perim(self):
        def test_rights_group(rg: RightGroupForManage):
            if rg.same_level_editor and rg.inf_level_editor:
                cases = sum([[self.simple_err_close_case.clone(
                    title=f"{rg.name}-on same level-hosp3-{role.help_text}",
                    user_rights=[rg.same_level_editor, rg.inf_level_reader],
                    initial_data=self.prepare_initial_data(
                        perimeter=self.hospital3,
                        role=role,
                    ),
                ), self.simple_err_close_case.clone(
                    title=f"{rg.name}-on inf levels-hosp2-{role.help_text}",
                    user_rights=[rg.inf_level_editor, rg.same_level_reader],
                    initial_data=self.prepare_initial_data(
                        perimeter=self.hospital2,
                        role=role,
                    ),
                )] for role in rg.manageable_roles], [])

                [self.check_close_case(case) for case in cases]
            for child in rg.children:
                test_rights_group(child)

        test_rights_group(self.right_groups_tree)

    def test_err_unfound_close_access_as_admin_wrong_perim(self):
        def test_rights_group(rg: RightGroupForManage):
            if rg.same_level_editor and rg.inf_level_editor:
                cases = sum([[self.simple_unf_close_case.clone(
                    title=f"{rg.name}-on same level-hosp3-{role.help_text}",
                    user_rights=[rg.same_level_editor, rg.same_level_reader],
                    initial_data=self.prepare_initial_data(
                        perimeter=self.hospital3,
                        role=role,
                    ),
                ), self.simple_unf_close_case.clone(
                    title=f"{rg.name}-edit same/read same-aphp"
                          f"-{role.help_text}",
                    user_rights=[rg.same_level_editor, rg.same_level_reader],
                    initial_data=self.prepare_initial_data(
                        perimeter=self.aphp,
                        role=role,
                    ),
                ), self.simple_unf_close_case.clone(
                    title=f"{rg.name}-edit same/read inf-aphp-{role.help_text}",
                    user_rights=[rg.same_level_editor, rg.inf_level_reader],
                    initial_data=self.prepare_initial_data(
                        perimeter=self.aphp,
                        role=role,
                    ),
                ), self.simple_unf_close_case.clone(
                    title=f"{rg.name}-edit same/read inf-hosp2"
                          f"-{role.help_text}",
                    user_rights=[rg.same_level_editor, rg.inf_level_reader],
                    initial_data=self.prepare_initial_data(
                        perimeter=self.hospital2,
                        role=role,
                    ),
                ), self.simple_unf_close_case.clone(
                    title=f"{rg.name}-edit inf/read same"
                          f"-hosp3-{role.help_text}",
                    user_rights=[rg.inf_level_editor, rg.same_level_reader],
                    initial_data=self.prepare_initial_data(
                        perimeter=self.hospital3,
                        role=role,
                    ),
                ), self.simple_unf_close_case.clone(
                    title=f"{rg.name}-edit inf/read same-aphp-{role.help_text}",
                    user_rights=[rg.inf_level_editor, rg.same_level_reader],
                    initial_data=self.prepare_initial_data(
                        perimeter=self.aphp,
                        role=role,
                    ),
                ), self.simple_unf_close_case.clone(
                    title=f"{rg.name}-on inf levels-hosp2-{role.help_text}",
                    user_rights=[rg.inf_level_editor, rg.inf_level_reader],
                    initial_data=self.prepare_initial_data(
                        perimeter=self.hospital2,
                        role=role,
                    ),
                ), self.simple_unf_close_case.clone(
                    title=f"{rg.name}-on inf levels-aphp-{role.help_text}",
                    user_rights=[rg.inf_level_editor, rg.inf_level_reader],
                    initial_data=self.prepare_initial_data(
                        perimeter=self.aphp,
                        role=role,
                    ),
                )] for role in rg.manageable_roles], [])

                [self.check_close_case(case) for case in cases]
            for child in rg.children:
                test_rights_group(child)

        test_rights_group(self.right_groups_tree)
