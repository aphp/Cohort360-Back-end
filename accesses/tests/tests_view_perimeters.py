import os
import random
from typing import List, Iterable
from unittest import mock

from rest_framework import status
from rest_framework.test import force_authenticate

from accesses.models import Perimeter, Access, Role
from accesses.tests.tests_view_accesses import RightGroupForManage, \
    RIGHT_GROUPS, AccessListCase
from accesses.views import PerimeterViewSet, NestedPerimeterViewSet
from admin_cohort.settings import PERIMETERS_TYPES
from admin_cohort.tests_tools import random_str, \
    new_user_and_profile, ViewSetTests, ListCase, \
    SimplePerimSetup, CreateCase, CaseRetrieveFilter, PatchCase, DeleteCase
from admin_cohort.tools import prettify_json

CARE_SITES_URL = "/perimeters"


class ObjectView(object):
    def __init__(self, d):
        self.__dict__ = d


# TEST CASES #################################################################


class PerimeterCaseRetrieveFilter(CaseRetrieveFilter):
    def __init__(self, name: str = "", **kwargs):
        self.name = name
        super(PerimeterCaseRetrieveFilter, self).__init__(**kwargs)


class TreefyListCase(ListCase):
    def __init__(self, to_exclude: List[Perimeter] = None, **kwargs):
        self.to_exclude = to_exclude or []
        super(TreefyListCase, self).__init__(**kwargs)


class PerimeterListCase(AccessListCase):
    def __init__(self, to_exclude: List[Perimeter] = None,
                 user_perimeters: List[Perimeter] = None, **kwargs):
        self.to_exclude = to_exclude or []
        self.user_perimeters = user_perimeters or []
        super(PerimeterListCase, self).__init__(**kwargs)


# ACTUAL TESTS #################################################################


class PerimeterTests(ViewSetTests):
    objects_url = "/perimeters/"
    retrieve_view = PerimeterViewSet.as_view({'get': 'retrieve'})
    list_view = PerimeterViewSet.as_view({'get': 'list'})
    create_view = PerimeterViewSet.as_view({'post': 'create'})
    delete_view = PerimeterViewSet.as_view({'delete': 'destroy'})
    update_view = PerimeterViewSet.as_view({'patch': 'partial_update'})
    close_view = PerimeterViewSet.as_view({'patch': 'close'})

    model = Perimeter
    model_objects = Perimeter.objects
    model_fields = Perimeter._meta.fields

    restricted_list_view = PerimeterViewSet.as_view({'get': 'get_manageable_perimeters'})

    def setUp(self):
        super(PerimeterTests, self).setUp()

        self.admin_user, self.admin_profile = new_user_and_profile(
            p_name='admin', provider_id=1000000,
            firstname="Cid", lastname="Kramer", email='cid@aphp.fr'
        )
        self.user_no_right, _ = new_user_and_profile(
            p_name='user_no_right', provider_id=2000000,
            firstname="Squall", lastname="Leonheart", email='s.l@aphp.fr'
        )

    def check_treefy(self, case: TreefyListCase, other_view: any = None):
        request = self.factory.get(
            path=case.url or self.objects_url,
            data=[] if case.url else case.params)
        force_authenticate(request, case.user)
        response = other_view(request) if other_view \
            else self.__class__.list_view(request)
        response.render()
        self.assertEqual(
            response.status_code, case.status,
            msg=(f"{case.title}: "
                 + prettify_json(response.content) if response.content else ""),
        )

        if not case.success:
            return

        res = response.data
        to_exclude_ids = [p.pk for p in case.to_exclude]

        def check_list(to_find: Iterable[Perimeter], found: List[dict],
                       level: int = 0, parent_id: str = ''):
            found_objs = [ObjectView(f) for f in found]

            to_find_ids = [p.pk for p in to_find]
            found_ids = [o.id for o in found_objs]

            self.assertCountEqual(
                to_find_ids, found_ids,
                msg=f"Level {level} - parent {parent_id} - {case.description}")

            for obj in found_objs:
                try:
                    matching = next(f for f in to_find if f.pk == obj.id)
                except Exception:
                    self.fail()

                check_list(matching.children.exclude(pk__in=to_exclude_ids),
                           getattr(obj, 'children', []), level + 1, obj.id)

        check_list(case.to_find, res)


class PerimeterGetTests(PerimeterTests):
    def setUp(self):
        super(PerimeterGetTests, self).setUp()
        nb_base_perims = 20
        ids = iter(range(1500))
        self.name_pattern = "aaa"

        def rand_name(i, j):
            return random_str(
                random.randint(i, j),
                self.name_pattern if random.random() > 0.5 else '')

        self.perims: List[Perimeter] = Perimeter.objects.bulk_create([
            Perimeter(
                local_id=str(next(ids)),
                name=rand_name(6, 15),
                type_source_value=PERIMETERS_TYPES[0],
                source_value=rand_name(6, 15),
            )
        ])

        for p in self.perims[0:nb_base_perims]:
            nb_children = random.randint(2, 8)
            children = Perimeter.objects.bulk_create([
                Perimeter(
                    local_id=str(next(ids)),
                    name=rand_name(6, 15),
                    parent=p,
                    type_source_value=PERIMETERS_TYPES[1],
                    source_value=rand_name(6, 15)
                ) for _ in range(nb_children)
            ])
            self.perims += children

            for c in children:
                nb_children = random.randint(2, 8)
                self.perims += Perimeter.objects.bulk_create([
                    Perimeter(
                        local_id=str(next(ids)),
                        name=rand_name(6, 15),
                        parent=c,
                        type_source_value=PERIMETERS_TYPES[2],
                        source_value=rand_name(6, 15)
                    ) for _ in range(nb_children)
                ])

    def test_get_all_cs(self):
        # As a simple user, I can get all perimeters in a list view
        case = ListCase(
            to_find=self.perims,
            user=self.user_no_right,
            success=True,
            status=status.HTTP_200_OK,
        )
        self.check_get_paged_list_case(case)

    def test_get_list_with_params(self):
        # As a simple user,
        # I can get perimeters filtered given query parameters
        basic_case_dict = dict(success=True, status=status.HTTP_200_OK,
                               user=self.user_no_right)
        cases = [
            ListCase(
                **basic_case_dict,
                title=f"name={self.name_pattern}",
                to_find=[
                    perim for perim in self.perims
                    if self.name_pattern in perim.name],
                params=dict(name=self.name_pattern)
            ),
            ListCase(
                **basic_case_dict,
                title=f"type_source_value={PERIMETERS_TYPES[1]}",
                to_find=[
                    perim for perim in self.perims
                    if PERIMETERS_TYPES[1] == perim.type_source_value],
                params=dict(type_source_value=PERIMETERS_TYPES[1])
            ),
            ListCase(
                **basic_case_dict,
                title=f"source_value={self.name_pattern}",
                to_find=[
                    perim for perim in self.perims
                    if self.name_pattern in perim.source_value],
                params=dict(source_value=self.name_pattern)
            ),
        ]
        [self.check_get_paged_list_case(case) for case in cases]

    def test_get_all_cs_treefied(self):
        # As a simple user, I can get all perimeters in a tree view
        case = TreefyListCase(
            to_find=[p for p in self.perims
                     if p.type_source_value == PERIMETERS_TYPES[0]],
            user=self.user_no_right,
            success=True,
            status=status.HTTP_200_OK,
            params=dict(treefy=True),
        )
        self.check_treefy(case)

    def test_get_list_with_params_treefied(self):
        # As a simple user,
        # I can get perimeters filtered given query parameters in a tree view
        basic_case_dict = dict(success=True, status=status.HTTP_200_OK,
                               user=self.user_no_right)
        cases = [
            TreefyListCase(
                **basic_case_dict,
                title=f"name={self.name_pattern}",
                to_find=[self.perims[0]],
                params=dict(treefy=True, name=self.name_pattern),
                to_exclude=[
                    perim for perim in self.perims
                    if (self.name_pattern not in perim.name
                        and all([
                                (self.name_pattern not in c.name
                                 and all([self.name_pattern not in cc.name
                                          for cc in c.children.all()]))
                                for c in perim.children.all()])
                        )],
            ),
            TreefyListCase(
                **basic_case_dict,
                title=f"type_source_value={PERIMETERS_TYPES[1]}",
                to_find=[self.perims[0]],
                params=dict(treefy=True, type_source_value=PERIMETERS_TYPES[1]),
                to_exclude=[perim for perim in self.perims
                            if PERIMETERS_TYPES[2] == perim.type_source_value],
            ),
            TreefyListCase(
                **basic_case_dict,
                title=f"source_value={self.name_pattern}",
                to_find=[self.perims[0]],
                params=dict(treefy=True, source_value=self.name_pattern),
                to_exclude=[
                    perim for perim in self.perims
                    if (self.name_pattern not in perim.source_value
                        and all([
                                (self.name_pattern not in c.source_value
                                 and all([self.name_pattern
                                          not in cc.source_value
                                          for cc in c.children.all()]))
                                for c in perim.children.all()])
                        )],
            ),
        ]
        [self.check_treefy(case) for case in cases]

    def test_get_children(self):
        # As a simple user, I can get the children of a perimeter
        [self.check_get_paged_list_case(ListCase(
            status=status.HTTP_200_OK,
            success=True,
            user=self.user_no_right,
            to_find=list(p.children.all())
        ), NestedPerimeterViewSet.as_view({'get': 'list'}), parent=p.id)
            for p in [
            self.perims[0],
            self.perims[0].children.first(),
            self.perims[0].children.first().children.first(),
        ]]


class PerimeterGetManageableTests(PerimeterTests, SimplePerimSetup):
    manageable_view = PerimeterViewSet.as_view({'get': 'get_manageable_perimeters'})

    def setUp(self):
        super(PerimeterGetManageableTests, self).setUp()
        SimplePerimSetup.setUp(self)
        self.user_with_right, self.prof_with_right = new_user_and_profile(
            email="with@righ.t")

        self.right_groups_tree: RightGroupForManage = \
            RightGroupForManage.clone_from_right_group(RIGHT_GROUPS)
        self.simple_get_case = PerimeterListCase(
            user=self.user_with_right,
            user_profile=self.prof_with_right,
            success=True,
            user_perimeter=self.hospital2,
            status=status.HTTP_200_OK,
            user_role=None,
            to_exlude=[]
        )

    def check_treefy(self, case: PerimeterListCase, other_view: any = None):
        r = Role.objects.create(**dict([(r, True)
                                        for r in case.user_rights]))
        if len(case.user_perimeters) > 0:
            user_accesses: List[Access] = Access.objects.bulk_create(
                [Access(role=r, profile=case.user_profile,
                        perimeter_id=p.id)
                 for p in case.user_perimeters]
            )

        else:
            user_accesses: List[Access] = [Access.objects.create(
                role=r, profile=case.user_profile,
                perimeter_id=case.user_perimeter.id)]

        request = self.factory.get(
            path=case.url or self.objects_url,
            data=[] if case.url else case.params)
        force_authenticate(request, case.user)
        response = other_view(request) if other_view \
            else self.__class__.list_view(request)
        response.render()
        self.assertEqual(
            response.status_code, case.status,
            msg=(f"{case.title}: "
                 + prettify_json(response.content) if response.content else ""),
        )

        if not case.success:
            return

        res = response.data
        to_exclude_ids = [p.pk for p in case.to_exclude]

        def check_list(to_find: Iterable[Perimeter], found: List[dict],
                       level: int = 0, parent_id: str = ''):
            found_objs = [ObjectView(f) for f in found]

            to_find_ids = [p.pk for p in to_find]
            found_ids = [o.id for o in found_objs]

            self.assertCountEqual(
                to_find_ids, found_ids,
                msg=f"Level {level} - parent {parent_id} - {case.description}")

            for obj in found_objs:
                try:
                    matching = next(f for f in to_find if f.pk == obj.id)
                except Exception:
                    self.fail()

                check_list(matching.children.exclude(pk__in=to_exclude_ids),
                           getattr(obj, 'children', []), level + 1, obj.id)

        check_list(case.to_find, res)
        [acc.delete() for acc in user_accesses]

    @mock.patch.dict(os.environ, {"SERVER_VERSION": "dev"})
    def test_manageable_as_any_admin(self):
        # (tree view) As a user...
        def test_rights_group(rg: RightGroupForManage):
            has_children: bool = len(rg.children) > 0
            if rg.same_level_editor and rg.inf_level_editor:
                cases = [self.simple_get_case.clone(
                    # ...with the right to manage accesses on the same level
                    # of a perimeter P, manageable will return the perimeter P
                    title=f"{rg.name}-on same level",
                    user_rights=[rg.same_level_editor],
                    to_find=[self.hospital2] if has_children else [],
                    to_exclude=[self.hospital3]
                ), self.simple_get_case.clone(
                    # with the right to manage accesses on the inferior levels
                    # of a perimeter P,
                    # manageable will return the perimeter P's children
                    title=f"{rg.name}-on inferiors levels",
                    user_rights=[rg.inf_level_editor],
                    to_find=[self.hospital3] if has_children else [],
                ), self.simple_get_case.clone(
                    # with the right to manage accesses on both same and
                    # inferior levels of a perimeter P,
                    # manageable will return the perimeter P's children
                    title=f"{rg.name}-on both levels",
                    user_rights=[rg.inf_level_editor, rg.same_level_editor],
                    to_find=[self.hospital2] if has_children else [],
                ), self.simple_get_case.clone(
                    # with the right to manage accesses on both same and
                    # inferior levels of a perimeter P and one of its siblings,
                    # manageable will return the two perimeters
                    # with their children
                    title=f"{rg.name}-on both levels - with hosp1",
                    user_rights=[rg.inf_level_editor, rg.same_level_editor],
                    to_find=([self.hospital1, self.hospital2]
                             if has_children else []),
                    user_perimeters=[self.hospital2, self.hospital1],
                ), self.simple_get_case.clone(
                    # with the right to manage accesses on the inferior
                    # levels of the top level,
                    # manageable will return all perimeters except the top one
                    title=f"{rg.name}-on top level's inferior levels",
                    user_rights=[rg.inf_level_editor],
                    to_find=([self.hospital1, self.hospital2]
                             if has_children else []),
                    user_perimeter=self.aphp,
                ), self.simple_get_case.clone(
                    # with the right to manage accesses on both same and
                    # inferior levels of the top level,
                    # manageable will return all perimeters
                    # except most inferior perimeter if nb_levels=2
                    title=f"{rg.name}-on both levels",
                    user_rights=[rg.inf_level_editor, rg.same_level_editor],
                    to_find=[self.aphp] if has_children else [],
                    user_perimeter=self.aphp,
                    params=dict(nb_levels=2),
                    to_exclude=[self.hospital3],
                ), self.simple_get_case.clone(
                    title=f"{rg.name}-on no levels",
                    user_rights=[rg.inf_level_reader, rg.same_level_reader],
                    to_find=[],
                )]
            else:
                cases = sum([[self.simple_get_case.clone(
                    # with the right to manage accesses on any perimeter,
                    # manageable will return all perimeters
                    title=f"{rg.name}-with {right}",
                    user_rights=[right],
                    to_find=[self.aphp] if has_children else [],
                )] for right in rg.rights], [])

            [self.check_treefy(case, self.__class__.manageable_view)
             for case in cases]
            for child in rg.children:
                test_rights_group(child)

        test_rights_group(self.right_groups_tree)


class PerimeterWithFullAdminTests(PerimeterTests, SimplePerimSetup):
    # As a user with all the rights...
    def setUp(self):
        super(PerimeterWithFullAdminTests, self).setUp()
        SimplePerimSetup.setUp(self)

        self.user_full_admin, prof_full_admin = new_user_and_profile(
            email='full@adm.in')
        role_full: Role = Role.objects.create(**dict([
            (f, True) for f in self.all_rights
        ]), name='FULL')
        Access.objects.create(profile=prof_full_admin,
                              perimeter_id=self.aphp.id, role=role_full)

    def test_err_create_perim(self):
        # ... I cannot create a perimeter
        test_name = "test"
        self.check_create_case(CreateCase(
            success=False,
            status=status.HTTP_403_FORBIDDEN,
            retrieve_filter=PerimeterCaseRetrieveFilter(name=test_name),
            user=self.user_full_admin,
            data=dict(id=10, name=test_name)
        ))

    def test_err_patch_perim(self):
        # ... I cannot edit a perimeter
        test_name = "test"
        self.check_patch_case(PatchCase(
            success=False,
            status=status.HTTP_403_FORBIDDEN,
            retrieve_filter=PerimeterCaseRetrieveFilter(name=test_name),
            user=self.user_full_admin,
            initial_data=dict(id=10, name=test_name),
            data_to_update=dict(name="new"),
        ))

    def test_err_delete_perim(self):
        # ... I cannot delete a perimeter
        test_name = "test"
        self.check_delete_case(DeleteCase(
            success=False,
            status=status.HTTP_403_FORBIDDEN,
            retrieve_filter=PerimeterCaseRetrieveFilter(name=test_name),
            user=self.user_full_admin,
            data_to_delete=dict(id=10, name=test_name),
        ))
