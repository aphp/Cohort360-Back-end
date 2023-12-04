import random
from itertools import product
from typing import List

from rest_framework import status

from accesses.models import Access, Role
from accesses.tests.old._tests_view_accesses import RightGroupForManage, \
    RIGHT_GROUPS, AccessListCase, any_manager_rights
from accesses.views import RoleViewSet
from admin_cohort.tools.tests_tools import random_str, new_user_and_profile, \
    CaseRetrieveFilter, ViewSetTestsWithBasicPerims, ListCase, \
    CreateCase, DeleteCase, PatchCase


class ObjectView(object):
    def __init__(self, d):
        self.__dict__ = d


class RoleTests(ViewSetTestsWithBasicPerims):
    unupdatable_fields = []
    unsettable_default_fields = dict()
    unsettable_fields = ["id"]
    manual_dupplicated_fields = []

    objects_url = "/roles/"
    retrieve_view = RoleViewSet.as_view({'get': 'retrieve'})
    list_view = RoleViewSet.as_view({'get': 'list'})
    create_view = RoleViewSet.as_view({'post': 'create'})
    delete_view = RoleViewSet.as_view({'delete': 'destroy'})
    update_view = RoleViewSet.as_view({'patch': 'partial_update'})
    model = Role
    model_objects = Role.objects
    model_fields = Role._meta.fields

    def setUp(self):
        super(RoleTests, self).setUp()

        # ROLES
        self.role_full: Role = Role.objects.create(**dict([
            (f, True) for f in self.all_rights
        ]), name='FULL')

        # Users
        # can_mng_roles
        self.user_that_can_mng_roles, self.prof_that_can_mng_roles = \
            new_user_and_profile(email="can@mng.roles")
        self.role_mng_roles = Role.objects.create(right_full_admin=True)
        Access.objects.create(
            perimeter_id=self.hospital3.id,
            profile=self.prof_that_can_mng_roles,
            role=self.role_mng_roles
        )

        # cannot_mng_roles
        self.user_that_cannot_mng_roles, self.prof_that_cannot_mng_roles = \
            new_user_and_profile(email="cannot@mng.roles")
        self.role_all_but_edit_roles = Role.objects.create(
            **dict([(r, True) for r in self.all_rights
                    if r != 'right_full_admin']))
        Access.objects.create(
            perimeter_id=self.aphp.id,
            profile=self.prof_that_cannot_mng_roles,
            role=self.role_all_but_edit_roles
        )


class RoleCaseRetrieveFilter(CaseRetrieveFilter):
    def __init__(self, name: str, exclude: dict = None):
        self.name = name
        super(RoleCaseRetrieveFilter, self).__init__(exclude=exclude)


class RoleGetListTests(RoleTests):
    def setUp(self):
        super(RoleGetListTests, self).setUp()
        # can_read_roles
        self.user_with_no_right, self.prof_with_no_right = \
            new_user_and_profile(email="with@no.right")

        self.name_pattern = "pat"

        nb_roles = 500

        self.role_names = [
                              random_str(random.randint(4, 8)) for _ in
                              range(nb_roles - 110)
                          ] + [
                              random_str(random.randint(1, 3))
                              + self.name_pattern
                              + random_str(random.randint(0, 3)) for _ in
                              range(110)
                          ]

        self.list_roles: List[Role] = Role.objects.bulk_create([Role(
            **{
                'name': name,
                **dict([(r, random.choice([True, False]))
                        for r in self.all_rights])
            }
        ) for name in self.role_names]) + [
                                          self.role_full, self.role_mng_roles,
                                          self.role_all_but_edit_roles]

    def test_get_all_roles(self):
        # As a user with no right, I can get all roles
        case = ListCase(
            to_find=[*self.list_roles],
            success=True,
            status=status.HTTP_200_OK,
            user=self.user_with_no_right
        )
        self.check_get_paged_list_case(case)

    def test_get_list_with_params(self):
        # As a user with no right, I can get roles filtered
        # given query parameters
        basic_case_dict = dict(success=True, status=status.HTTP_200_OK,
                               user=self.user_with_no_right)
        cases = [
            ListCase(
                **basic_case_dict,
                title=f"name={self.name_pattern}",
                to_find=[
                    role for role in self.list_roles
                    if str(self.name_pattern) in str(role.name)],
                params=dict(name=self.name_pattern)
            ),
            *[ListCase(
                **basic_case_dict,
                title=f"{right}=True",
                to_find=[role for role in self.list_roles
                         if getattr(role, right)],
                params={right: True}
            ) for right in self.all_rights],
        ]
        [self.check_get_paged_list_case(case) for case in cases]


class RoleGetAssignableTests(RoleTests):
    assignable_view = RoleViewSet.as_view({'get': 'assignable'})

    def setUp(self):
        super(RoleGetAssignableTests, self).setUp()

        self.user_with_right, self.prof_with_right = new_user_and_profile(
            email="with@righ.t")
        self.role_full.delete()
        self.role_mng_roles.delete()
        self.role_all_but_edit_roles.delete()

        self.right_groups_tree: RightGroupForManage = \
            RightGroupForManage.clone_from_right_group(RIGHT_GROUPS)
        self.simple_get_case = AccessListCase(
            user=self.user_with_right,
            user_profile=self.prof_with_right,
            user_perimeter=self.hospital2,
            success=True,
            status=status.HTTP_200_OK,
            user_role=None,
        )

        def add_roles_to_right_groups_tree(
                rg: RightGroupForManage, parent: RightGroupForManage = None
        ):
            rg.full_role = Role.objects.create(
                **dict([(f, True) for f in rg.rights
                        + (any_manager_rights if rg.is_manager_admin else [])
                        ]))
            rg.full_role_with_any_from_child = [
                Role.objects.create(
                    **dict([
                        (f, True) for f in
                        rg.rights
                        + (any_manager_rights if rg.is_manager_admin else [])
                        + [right]
                    ])) for right in rg.all_child_groups_rights()
            ]
            rg.full_role_with_any_from_direct_child = [
                r for r in rg.full_role_with_any_from_child
                if any(getattr(r, right) for right
                       in rg.all_child_groups_rights(r=False))]

            if parent:
                rg.siblings_rights = parent.all_child_groups_rights(
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

            for child in rg.child_groups:
                add_roles_to_right_groups_tree(child, rg)

        add_roles_to_right_groups_tree(self.right_groups_tree)

    def check_get_role_paged_list_case(
            self, case: AccessListCase, other_view: any = None, **view_kwargs):
        r = Role.objects.create(**dict([(r, True)
                                        for r in case.user_rights]))
        user_access: Access = Access.objects.create(
            role=r, profile=case.user_profile,
            perimeter_id=case.user_perimeter.id)
        if r.right_full_admin:
            case.to_find.append(r)

        self.check_get_paged_list_case(case, other_view, **view_kwargs)
        user_access.delete()
        r.delete()

    def test_get_assignable_as_any_admin(self):
        # As a user with a right to manage accesses, I can get the roles
        # I can assign to another user on a perimeter P given rules.md
        def test_rights_group(rg: RightGroupForManage):
            if rg.same_level_editor and rg.inf_level_editor:
                cases = [self.simple_get_case.clone(
                    title=f"{rg.name}-on same level-hosp2",
                    user_rights=[rg.same_level_editor],
                    to_find=rg.manageable_roles,
                    params=dict(perimeter_id=self.hospital2.id),
                ), self.simple_get_case.clone(
                    title=f"{rg.name}-on inferiors levels-hosp3",
                    user_rights=[rg.inf_level_editor],
                    to_find=rg.manageable_roles,
                    params=dict(perimeter_id=self.hospital3.id),
                ), self.simple_get_case.clone(
                    title=f"{rg.name}-on same level-hosp3",
                    user_rights=[rg.same_level_editor],
                    to_find=[],
                    params=dict(perimeter_id=self.hospital3.id),
                ), self.simple_get_case.clone(
                    title=f"{rg.name}-on same level-aphp",
                    user_rights=[rg.same_level_editor],
                    params=dict(perimeter_id=self.aphp.id),
                    to_find=[],
                ), self.simple_get_case.clone(
                    title=f"{rg.name}-on inferior levels-hosp2",
                    user_rights=[rg.inf_level_editor],
                    to_find=[],
                    params=dict(perimeter_id=self.hospital2.id),
                )]
            else:
                cases = [self.simple_get_case.clone(
                    title=f"{rg.name}-with {right}-{perim.name}",
                    user_rights=[right],
                    to_find=rg.manageable_roles,
                    params=dict(perimeter_id=perim.id),
                ) for (perim, right) in product(
                    [self.hospital1, self.aphp, self.hospital2, self.hospital3],
                    rg.rights)
                ]

            [self.check_get_role_paged_list_case(case,
                                                 self.__class__.assignable_view)
             for case in cases]
            for child in rg.child_groups:
                test_rights_group(child)

        test_rights_group(self.right_groups_tree)

    def test_err_get_assignable_missing_perimeter(self):
        # As a user with a right to manage accesses,
        # I cannot call _assignable_ without perimeter_id parameter
        rg = self.right_groups_tree
        cases = [self.simple_get_case.clone(
            title=f"{rg.name}-with {right}-{perim.name}",
            user_rights=[right],
            to_find=rg.manageable_roles,
            success=False,
            status=status.HTTP_400_BAD_REQUEST,
        ) for (perim, right) in product(
            [self.hospital1, self.aphp, self.hospital2, self.hospital3],
            rg.rights)
        ]
        [self.check_get_role_paged_list_case(case,
                                             self.__class__.assignable_view)
         for case in cases]


class RoleCreateTests(RoleTests):
    def setUp(self):
        super(RoleCreateTests, self).setUp()

        test_role_name = 'test_name'
        self.creation_data = {
            'name': test_role_name,
            **dict([(r, True) for r in self.all_rights])
        }
        self.basic_create_case = CreateCase(
            data=self.creation_data,
            retrieve_filter=RoleCaseRetrieveFilter(name=test_role_name),
            user=None, status=None, success=None,
        )

    def test_create_as_role_admin(self):
        # As a user with right_full_admin, I can create a new role
        case = self.basic_create_case.clone(
            user=self.user_that_can_mng_roles,
            success=True,
            status=status.HTTP_201_CREATED,
        )
        self.check_create_case(case)

    def test_error_create_as_simple_user(self):
        # As a user with everything but right_full_admin,
        # I cannot create a new role
        case = self.basic_create_case.clone(
            user=self.user_that_cannot_mng_roles,
            success=False,
            status=status.HTTP_403_FORBIDDEN,
        )
        self.check_create_case(case)


class RolePatchTests(RoleTests):
    def setUp(self):
        super(RolePatchTests, self).setUp()

        self.created_data = {
            'name': 'created',
            **dict([(r, True) for r in self.all_rights])
        }
        self.base_data_to_update = {
            'name': 'updated',
            **dict([(r, False) for r in self.all_rights])
        }
        self.basic_patch_case = PatchCase(
            initial_data=self.created_data,
            data_to_update=self.base_data_to_update,
            user=None, status=None, success=None,
        )

    def test_patch_as_user_admin(self):
        # As a user with right_full_admin, I can edit a role
        case = self.basic_patch_case.clone(
            user=self.user_that_can_mng_roles,
            success=True,
            status=status.HTTP_200_OK,
        )
        self.check_patch_case(case)

    def test_error_patch_as_simple_user(self):
        # As a user with everything but right_full_admin,
        # I cannot edit a role
        case = self.basic_patch_case.clone(
            user=self.user_that_cannot_mng_roles,
            success=False,
            status=status.HTTP_403_FORBIDDEN,
        )
        self.check_patch_case(case)


class RoleDeleteTests(RoleTests):
    def setUp(self):
        super(RoleDeleteTests, self).setUp()

        # user with all the rights
        self.user_full_admin, prof_full_admin = new_user_and_profile(
            email='full@admin.us')
        Access.objects.create(
            role=self.role_full,
            profile=prof_full_admin,
            perimeter_id=self.aphp.id
        )

        self.created_data = {
            'name': 'created',
            **dict([(r, True) for r in self.all_rights])
        }
        self.basic_delete_case = DeleteCase(
            data_to_delete=self.created_data,
            user=None, status=None, success=None,
        )

    # when we'll be safe with role deletion (cascade, deletion, etc.)
    # def test_delete_user_as_main_admin(self):
    #     # As a user with right_full_admin,
    #     # I can delete a role (set delete_datetime to now)
    #     case = self.basic_delete_case.clone(
    #         user=self.user_that_can_mng_roles,
    #         success=True,
    #         status=status.HTTP_204_NO_CONTENT,
    #     )
    #     self.check_delete_case(case)
    #
    # def test_error_delete_user_as_simple_user(self):
    #     # As a user with everything but right_full_admin,
    #     # I cannot delete a role
    #     case = self.basic_delete_case.clone(
    #         user=self.user_that_can_mng_roles,
    #         success=False,
    #         status=status.HTTP_403_FORBIDDEN,
    #     )
    #     self.check_delete_case(case)

    def test_error_delete_user_as_god_admin(self):
        # As a user with everything but right_full_admin,
        # I cannot delete a role
        case = self.basic_delete_case.clone(
            user=self.user_full_admin,
            success=False,
            status=status.HTTP_403_FORBIDDEN,
        )
        self.check_delete_case(case)
