# import random
# from datetime import timedelta
# from typing import List
#
# from django.utils import timezone
#
# from accesses.models import Access, Profile, get_user_accesses, Role, \
#     can_roles_manage_access, get_specific_roles, RoleType, \
#     get_assignable_roles_on_perimeter
# from admin_cohort.models import User
# from admin_cohort.tests_tools import BaseTests, BaseTestsWithMorePerimeters, \
#     new_user_and_profile
#
#
# # TODO : les logs
# # TODO: test règles pour update access (end/start_datetime)
# # TODO: test pour résultat d'api de manageable et l'autre
# # TODO: tests plus complets pour les clés api, comme pour les tests unitaires
#
#
# class ModelsUnitBaseTest(BaseTestsWithMorePerimeters):
#     def setUp(self):
#         super(ModelsUnitBaseTest, self).setUp()
#
#         self.access_10_admin: Access = Access.objects.create(
#             perimeter_id=self.perim0.id,
#             role=self.main_admin_role,
#             profile=self.admin_profile,
#         )
#         self.access_12_1_loc_admin: Access = Access.objects.create(
#             perimeter_id=self.perim12.id,
#             role=self.admin_role,
#             profile=self.profile1,
#         )
#         self.access_12_1_pseudo: Access = Access.objects.create(
#             perimeter_id=self.perim12.id,
#             role=self.pseudo_anonymised_data_role,
#             profile=self.profile1,
#         )
#         self.access_33_1_nominative: Access = Access.objects.create(
#             perimeter_id=self.perim33.id,
#             role=self.nominative_data_role,
#             profile=self.profile1,
#         )
#         self.access_23_1_outdated: Access = Access.objects.create(
#             perimeter_id=self.perim23.id,
#             role=self.admin_role,
#             profile=self.profile1.id,
#             end_datetime=timezone.now() - timedelta(days=2)
#         )
#         self.access_23_1_not_started: Access = Access.objects.create(
#             perimeter_id=self.perim23.id,
#             role=self.admin_manager_role,
#             profile=self.profile1.id,
#             start_datetime=timezone.now() + timedelta(days=2)
#         )
#         self.access_21_1_not_started: Access = Access.objects.create(
#             perimeter_id=self.perim23.id,
#             role=self.admin_manager_role,
#             profile=self.profile1.id,
#             start_datetime=timezone.now() + timedelta(days=2)
#         )
#         self.deleted_cs: Access = Access.objects.create(
#             perimeter_id=self.perim23.id,
#             role=self.admin_manager_role,
#             profile=self.profile1.id,
#             start_datetime=timezone.now() + timedelta(days=2),
#             delete_datetime=timezone.now()
#         )
#
#         self.profile1_2: Profile = Profile.objects.create(
#             provider_name='provider1',
#             source="ACTIVE",
#             provider_id=self.user1.provider_id,
#             provider_source_value=self.user1.provider_username,
#             is_active=True
#         )
#         self.access_ph2: Access = Access.objects.create(
#             perimeter_id=self.perim33.id,
#             role=self.nominative_data_role,
#             profile=self.profile1_2,
#         )
#
#         self.profile1_inactive: Profile = Profile.objects.create(
#             provider_name='provider1',
#             source="INACTIVE",
#             provider_id=self.user1.provider_id,
#             provider_source_value=self.user1.provider_username,
#             is_active=False
#         )
#         self.access_ph_inactive: Access = Access.objects.create(
#             perimeter_id=self.perim33.id,
#             role=self.nominative_data_role,
#             profile=self.profile1_inactive,
#         )
#
#         self.empty_rights = dict(
#             right_full_admin=False,
#
#             right_manage_users=False,
#             right_read_users=False,
#
#             right_manage_admin_accesses_same_level=False,
#             right_read_admin_accesses_same_level=False,
#             right_manage_admin_accesses_inferior_levels=False,
#             right_read_admin_accesses_inferior_levels=False,
#
#             right_manage_data_accesses_same_level=False,
#             right_read_data_accesses_same_level=False,
#             right_manage_data_accesses_inferior_levels=False,
#             right_read_data_accesses_inferior_levels=False,
#
#             right_read_patient_nominative=False,
#             right_read_patient_pseudonymized=False,
#         )
#
#     def role_rights(self, role: Role) -> str:
#         return "\n".join([r for r in self.empty_rights.keys()
#                           if getattr(role, r)])
#
#     def check_list_role(self, found: List[Role], to_find: List[Role],
#                         key: str = ""):
#         msg = f"{key} What was to find: \n {[r.name for r in to_find]}.\n " \
#               f"What was found: \n {[r.name for r in found]}"
#         self.assertEqual(len(to_find), len(found), msg)
#         found_ids = [r.id for r in found]
#         [
#             self.assertIn(r.id, found_ids,
#                           f"{msg}.\nMissing role {r.name} "
#                           f"has {self.role_rights(r)}")
#             for r in to_find]
#
#
# class ModelsUnitTest(ModelsUnitBaseTest):
#     def check_acc_list(self, acc_found: List[Access],
#                        acc_to_find: List[Access]):
#         acc_to_find_ids = [a.id for a in acc_to_find]
#         acc_found_ids = [a.id for a in acc_found]
#         msg = "\n".join(["", "got", str(acc_found_ids), "should be",
#                          str(acc_to_find_ids)])
#
#         self.assertEqual(len(acc_found), len(acc_to_find), msg=msg)
#         for i in acc_to_find_ids:
#             self.assertIn(i, acc_found_ids, msg=msg)
#
#     def test_not_retrieve_deleted_objects(self):
#         accs: Access = Access.objects.all()
#         self.assertNotIn(self.deleted_cs.id, [acc.id for acc in accs])
#
#         acc: Access = Access.objects.filter(
#         ).first()
#         self.assertIsNone(acc)
#
#         self.assertRaises(
#             Access.DoesNotExist, Access.objects.get,
#             id=self.deleted_cs.id
#         )
#
#
# class RoleManagingUnitTest(ModelsUnitBaseTest):
#     def setUp(self):
#         super(RoleManagingUnitTest, self).setUp()
#
#         self.mother_perim = self.perim12
#         self.child_perim = self.perim23
#
#         self.roles_contexts = dict()
#
#         def make_accesses(r: Role):
#             user_mother, prof_mother = new_user_and_profile()
#             user_child, prof_child = new_user_and_profile()
#
#             acc_child: Access = Access.objects.create(
#                 role=r,
#                 profile=prof_child,
#                 perimeter_id=self.child_perim.id,
#             )
#             acc_mother: Access = Access.objects.create(
#                 role=r,
#                 profile=prof_mother,
#                 perimeter_id=self.mother_perim.id,
#             )
#
#             self.roles_contexts[r.id] = dict(
#                 user_child=user_child, user_mother=user_mother,
#                 profile_child=prof_child, acc_child=acc_child,
#                 acc_mother=acc_mother, profile_mother=prof_mother
#             )
#
#         self.edit_role_admin_role = Role.objects.create(**{
#             **self.empty_rights,
#             'name': 'edit_role_admin_role',
#             'right_full_admin': True,
#         })
#         make_accesses(self.edit_role_admin_role)
#
#         self.admin_manager_role_same_level = Role.objects.create(**{
#             **self.empty_rights,
#             'name': 'admin_manager_role_same_level',
#             'right_read_users': True,
#             'right_manage_admin_accesses_same_level': True,
#             'right_read_admin_accesses_same_level': True,
#         })
#         make_accesses(self.admin_manager_role_same_level)
#         self.admin_manager_role_inf_level = Role.objects.create(**{
#             **self.empty_rights,
#             'name': 'admin_manager_role_inf_level',
#             'right_read_users': True,
#             'right_manage_admin_accesses_inferior_levels': True,
#             'right_read_admin_accesses_inferior_levels': True,
#         })
#         make_accesses(self.admin_manager_role_inf_level)
#
#         self.admin_role_same_level = Role.objects.create(**{
#             **self.empty_rights,
#             'name': 'admin_role_same_level',
#             'right_read_users': True,
#             'right_manage_data_accesses_same_level': True,
#             'right_read_data_accesses_same_level': True,
#         })
#         make_accesses(self.admin_role_same_level)
#         self.admin_role_inf_level = Role.objects.create(**{
#             **self.empty_rights,
#             'name': 'admin_role_inf_level',
#             'right_read_users': True,
#             'right_manage_data_accesses_inferior_levels': True,
#             'right_read_data_accesses_inferior_levels': True,
#         })
#         make_accesses(self.admin_role_inf_level)
#
#         self.full_admin_manager_role = Role.objects.create(**{
#             **self.empty_rights,
#             'name': 'full_admin_manager_role',
#             'right_read_users': True,
#             'right_full_admin': True,
#             'right_manage_users': True,
#             'right_manage_admin_accesses_same_level': True,
#             'right_read_admin_accesses_same_level': True,
#             'right_manage_admin_accesses_inferior_levels': True,
#             'right_read_admin_accesses_inferior_levels': True,
#         })
#         self.full_admin_role = Role.objects.create(**{
#             **self.empty_rights,
#             'name': 'full_admin_role',
#             'right_read_users': True,
#             'right_manage_data_accesses_same_level': True,
#             'right_read_data_accesses_same_level': True,
#             'right_manage_data_accesses_inferior_levels': True,
#             'right_read_data_accesses_inferior_levels': True,
#         })
#         self.full_data_access_role = Role.objects.create(**{
#             **self.empty_rights,
#             'name': 'full_data_access_role',
#             'right_read_patient_nominative': True,
#             'right_read_patient_pseudonymized': True,
#         })
#
#         self.non_admin_manager_roles = [
#             Role.objects.create(**{
#                 **self.empty_rights,
#                 'right_full_admin': True,
#                 'right_manage_users': True,
#                 'right_manage_admin_accesses_same_level': True,
#                 'right_read_admin_accesses_same_level': True,
#                 'right_manage_admin_accesses_inferior_levels': True,
#                 'right_read_admin_accesses_inferior_levels': True,
#                 list(self.empty_rights.keys())[i]: True,
#                 'right_read_users': True,
#             }) for i in list(range(8, len(self.empty_rights)))
#         ]
#         self.non_admin_roles = [
#             Role.objects.create(**{
#                 **self.empty_rights,
#                 'right_manage_data_accesses_same_level': True,
#                 'right_read_data_accesses_same_level': True,
#                 'right_manage_data_accesses_inferior_levels': True,
#                 'right_read_data_accesses_inferior_levels': True,
#                 list(self.empty_rights.keys())[i]: True,
#             }) for i in (list(range(0, 3)) + list(range(4, 8))
#                          + list(range(12, len(self.empty_rights))))
#         ]
#         self.non_data_acc_roles = [
#             Role.objects.create(**{
#                 **self.empty_rights,
#                 'right_read_patient_nominative': True,
#                 'right_read_patient_pseudonymized': True,
#                 list(self.empty_rights.keys())[i]: True,
#             }) for i in list(range(0, 3)) + list(range(4, 12))
#         ]
#
#     def test_can_main_admin_manage_admin_manager_access(self):
#         # Given accesses with edit role, I can give any access
#         # with edit_roles, user and admin managing rights
#
#         right_role_wrong_perim_cases = [
#         ]
#         acc = self.roles_contexts[
#             self.edit_role_admin_role.id]["acc_mother"]
#         right_role_right_perim_cases = [
#             dict(
#                 role=self.full_admin_manager_role,
#                 perimeter_id=self.mother_perim.id,
#                 access=(acc, self.edit_role_admin_role),
#                 expected=True,
#                 id=1,
#                 msg="As main_admin on child_perim, I should be able "
#                     "to manage admin_manager_role on mother_perim"
#             ),
#             dict(
#                 role=self.full_admin_manager_role,
#                 perimeter_id=self.child_perim.id,
#                 access=(acc, self.edit_role_admin_role),
#                 expected=True,
#                 id=2,
#                 msg="As main_admin on child_perim, "
#                     "I should be able to manage "
#                     "admin_manager_role on child_perim"
#             ),
#         ]
#
#         wrong_role_cases = [
#             dict(
#                 role=non_admin_manager_role,
#                 perimeter_id=self.mother_perim.id,
#                 access=(acc, self.admin_manager_role_same_level),
#                 expected=False,
#                 id=i + 3,
#                 msg="As main_admin on child_perim, "
#                     f"I should not be able to manage this "
#                     f"non_admin_manager_role on mother_perim: \n"
#                     f"{self.role_rights(non_admin_manager_role)}"
#             ) for (i, non_admin_manager_role)
#             in enumerate(self.non_admin_manager_roles)
#         ]
#
#         cases = (right_role_wrong_perim_cases + right_role_right_perim_cases
#                  + wrong_role_cases)
#         [self.assertEqual(can_roles_manage_access(
#             [c['access']], c['role'], c['perimeter_id']), c['expected'],
#             f"{c['id']}: {c['msg']}")
#             for c in cases]
#
#     def test_can_admin_manager_manage_admin_access(self):
#         # Given accesses with admin_managing rights, I can give any access
#         # with admin accesses, respecting the care-site hierarchy
#         acc_mother_same_level = self.roles_contexts[
#             self.admin_manager_role_same_level.id]['acc_mother']
#         acc_mother_inf_level = self.roles_contexts[
#             self.admin_manager_role_inf_level.id]['acc_mother']
#         right_role_wrong_perim_cases = [
#             dict(
#                 role=self.full_admin_role,
#                 perimeter_id=self.child_perim.id,
#                 access=(acc_mother_same_level,
#                         self.admin_manager_role_same_level),
#                 expected=False,
#                 id=1,
#                 msg="As admin_manager_role_same_level on mother_perim, "
#                     "I should not be able to manage admin_manager_role "
#                     "on child_perim"
#             ),
#             dict(
#                 role=self.full_admin_role,
#                 perimeter_id=self.mother_perim.id,
#                 access=(acc_mother_inf_level,
#                         self.admin_manager_role_inf_level),
#                 expected=False,
#                 id=2,
#                 msg="As admin_manager_role_inf_level on mother_perim, "
#                     "I should not be able to manage "
#                     "admin_manager_role on mother_perim"
#             ),
#         ]
#         right_role_right_perim_cases = [
#             dict(
#                 role=self.full_admin_role,
#                 perimeter_id=self.mother_perim.id,
#                 access=(acc_mother_same_level,
#                         self.admin_manager_role_same_level),
#                 expected=True,
#                 id=3,
#                 msg="As admin_manager_role_same_level on mother_perim, I " \
#                     "should be able to manage admin_manager_role " \
#                     "on mother_perim"
#             ),
#             dict(
#                 role=self.full_admin_role,
#                 perimeter_id=self.child_perim.id,
#                 access=(acc_mother_inf_level,
#                         self.admin_manager_role_inf_level),
#                 expected=True,
#                 id=4,
#                 msg="As admin_manager_role_inf_level on mother_perim, I should"
#                     " be able to manage admin_manager_role on child_perim"
#             ),
#         ]
#
#         wrong_role_cases = [
#                                dict(
#                                    role=non_admin_role,
#                                    perimeter_id=self.mother_perim.id,
#                                    access=(acc_mother_same_level,
#                                            self.admin_manager_role_same_level),
#                                    expected=False,
#                                    id=i + 5,
#                                    msg=f"As admin_manager_role_same_level " \
#                                        f"on mother_perim, I should not be " \
#                                        f"able to manage this non_admin_role "
#                                        f"on mother_perim: \n"
#                                        f"{self.role_rights(non_admin_role)}"
#                                ) for (i, non_admin_role) in
#                                enumerate(self.non_admin_roles)
#                            ] + [
#                                dict(
#                                    role=non_admin_role,
#                                    perimeter_id=self.child_perim.id,
#                                    access=(acc_mother_inf_level,
#                                            self.admin_manager_role_inf_level),
#                                    expected=False,
#                                    id=i + 5 + len(self.non_admin_roles),
#                                    msg=f"As admin_manager_role_inf_level on " \
#                                        f"mother_perim, I should not be able " \
#                                        f"to manage this non_admin_role on " \
#                                        f"child_perim: \n"
#                                        f"{self.role_rights(non_admin_role)}"
#                                ) for (i, non_admin_role) in
#                                enumerate(self.non_admin_roles)
#                            ]
#
#         cases = (right_role_wrong_perim_cases + right_role_right_perim_cases
#                  + wrong_role_cases)
#         [self.assertEqual(can_roles_manage_access(
#             [c['access']], c['role'], c['perimeter_id']), c['expected'],
#             f"{c['id']}: {c['msg']}")
#             for c in cases]
#
#     def test_can_admin_manage_data_access(self):
#         # Given accesses with admin rights, I can give any access
#         # with data access, respecting the care-site hierarchy
#         acc_mother_same_level = self.roles_contexts[
#             self.admin_role_same_level.id]['acc_mother']
#         acc_mother_inf_level = self.roles_contexts[
#             self.admin_role_inf_level.id]['acc_mother']
#         right_role_wrong_perim_cases = [
#             dict(
#                 role=self.full_data_access_role,
#                 perimeter_id=self.child_perim.id,
#                 access=(acc_mother_same_level, self.admin_role_same_level),
#                 expected=False,
#                 id=1,
#                 msg="As admin_role_same_level on mother_perim, "
#                     "I should not be able to manage admin_role on child_perim"
#             ),
#             dict(
#                 role=self.full_data_access_role,
#                 perimeter_id=self.mother_perim.id,
#                 access=(acc_mother_inf_level, self.admin_role_inf_level),
#                 expected=False,
#                 id=2,
#                 msg="As admin_role_inf_level on mother_perim, "
#                     "I should not be able to manage admin_role on mother_perim"
#             ),
#         ]
#         right_role_right_perim_cases = [
#             dict(
#                 role=self.full_data_access_role,
#                 perimeter_id=self.mother_perim.id,
#                 access=(acc_mother_same_level, self.admin_role_same_level),
#                 expected=True,
#                 id=3,
#                 msg="As admin_role_same_level on mother_perim, "
#                     "I should be able to manage admin_role on mother_perim"
#             ),
#             dict(
#                 role=self.full_data_access_role,
#                 perimeter_id=self.child_perim.id,
#                 access=(acc_mother_inf_level, self.admin_role_inf_level),
#                 expected=True,
#                 id=4,
#                 msg="As admin_role_inf_level on mother_perim, "
#                     "I should be able to manage admin_role on child_perim"
#             ),
#         ]
#
#         wrong_role_cases = [
#                                dict(
#                                    role=non_data_acc_role,
#                                    perimeter_id=self.mother_perim.id,
#                                    access=(acc_mother_same_level,
#                                            self.admin_role_same_level),
#                                    expected=False,
#                                    id=i + 5,
#                                    msg=f"As admin_role_same_level on " \
#                                        f"mother_perim, I should not be able " \
#                                        f"to manage this non_data_acc_role " \
#                                        f"on mother_perim: \n"
#                                        f"{self.role_rights(non_data_acc_role)}"
#                                ) for (i, non_data_acc_role)
#                                in enumerate(self.non_data_acc_roles)
#                            ] + [
#                                dict(
#                                    role=non_data_acc_role,
#                                    perimeter_id=self.child_perim.id,
#                                    access=(acc_mother_inf_level,
#                                            self.admin_role_inf_level),
#                                    expected=False,
#                                    id=i + 5 + len(self.non_data_acc_roles),
#                                    msg=f"As admin_role_inf_level " \
#                                        f"on mother_perim, I should not be " \
#                                        f"able to manage this " \
#                                        f"non_data_acc_role on " \
#                                        f"child_perim: \n"
#                                        f"{self.role_rights(non_data_acc_role)}"
#                                ) for (i, non_data_acc_role)
#                                in enumerate(self.non_data_acc_roles)
#                            ]
#
#         cases = (right_role_wrong_perim_cases + right_role_right_perim_cases
#                  + wrong_role_cases)
#         [self.assertEqual(can_roles_manage_access(
#             [c['access']], c['role'], c['perimeter_id']), c['expected'],
#             f"{c['id']}: {c['msg']}")
#             for c in cases]
#
#     def test_get_assignable_roles_on_perimeter_for_main_admin(self):
#         cases = [
#             dict(
#                 user=self.roles_contexts[
#                     self.edit_role_admin_role.id
#                 ]['user_child'],
#                 perimeter=self.child_perim,
#                 expected=[self.full_admin_manager_role, self.main_admin_role,
#                           self.admin_manager_role, self.edit_role_admin_role,
#                           self.admin_manager_role_inf_level,
#                           self.admin_manager_role_same_level]
#             ),
#             dict(
#                 user=self.roles_contexts[
#                     self.edit_role_admin_role.id
#                 ]['user_child'],
#                 perimeter=self.mother_perim,
#                 expected=[self.full_admin_manager_role, self.main_admin_role,
#                           self.admin_manager_role, self.edit_role_admin_role,
#                           self.admin_manager_role_inf_level,
#                           self.admin_manager_role_same_level]
#             ),
#         ]
#
#         [self.check_list_role(
#             get_assignable_roles_on_perimeter(
#                 c['user'].pk, c['perimeter'].id
#             ), c['expected']) for c in cases]
#
#     def test_get_assignable_roles_on_perimeter_for_admin_manager(self):
#         cases = [
#             dict(
#                 user=self.roles_contexts[
#                     self.admin_manager_role_same_level.id
#                 ]['user_child'],
#                 perimeter=self.child_perim,
#                 expected=[self.admin_role, self.full_admin_role,
#                           self.admin_role_same_level,
#                           self.admin_role_inf_level]
#             ),
#             dict(
#                 user=self.roles_contexts[
#                     self.admin_manager_role_same_level.id
#                 ]['user_child'],
#                 perimeter=self.mother_perim,
#                 expected=[]
#             ),
#             dict(
#                 user=self.roles_contexts[
#                     self.admin_manager_role_inf_level.id
#                 ]['user_child'],
#                 perimeter=self.child_perim,
#                 expected=[]
#             ),
#             dict(
#                 user=self.roles_contexts[
#                     self.admin_manager_role_inf_level.id
#                 ]['user_child'],
#                 perimeter=self.mother_perim,
#                 expected=[]
#             ),
#             dict(
#                 user=self.roles_contexts[
#                     self.admin_manager_role_same_level.id
#                 ]['user_mother'],
#                 perimeter=self.child_perim,
#                 expected=[]
#             ),
#             dict(
#                 user=self.roles_contexts[
#                     self.admin_manager_role_same_level.id
#                 ]['user_mother'],
#                 perimeter=self.mother_perim,
#                 expected=[self.admin_role, self.full_admin_role,
#                           self.admin_role_same_level,
#                           self.admin_role_inf_level]
#             ),
#             dict(
#                 user=self.roles_contexts[
#                     self.admin_manager_role_inf_level.id
#                 ]['user_mother'],
#                 perimeter=self.child_perim,
#                 expected=[self.admin_role, self.full_admin_role,
#                           self.admin_role_same_level,
#                           self.admin_role_inf_level]
#             ),
#             dict(
#                 user=self.roles_contexts[
#                     self.admin_manager_role_inf_level.id
#                 ]['user_mother'],
#                 perimeter=self.mother_perim,
#                 expected=[]
#             ),
#         ]
#         [self.check_list_role(
#             get_assignable_roles_on_perimeter(c['user'].pk, c['perimeter'].id),
#             c['expected']) for c in cases]
#
#     def test_get_assignable_roles_on_perimeter_for_admin(self):
#         cases = [
#             dict(
#                 user=self.roles_contexts[
#                     self.admin_role_same_level.id
#                 ]['user_child'],
#                 perimeter=self.child_perim,
#                 expected=[self.pseudo_anonymised_data_role,
#                           self.nominative_data_role,
#                           self.full_data_access_role]
#             ),
#             dict(
#                 user=self.roles_contexts[
#                     self.admin_role_same_level.id
#                 ]['user_child'],
#                 perimeter=self.mother_perim,
#                 expected=[]
#             ),
#             dict(
#                 user=self.roles_contexts[
#                     self.admin_role_inf_level.id
#                 ]['user_child'],
#                 perimeter=self.child_perim,
#                 expected=[]
#             ),
#             dict(
#                 user=self.roles_contexts[
#                     self.admin_role_inf_level.id
#                 ]['user_child'],
#                 perimeter=self.mother_perim,
#                 expected=[]
#             ),
#             dict(
#                 user=self.roles_contexts[
#                     self.admin_role_same_level.id
#                 ]['user_mother'],
#                 perimeter=self.child_perim,
#                 expected=[]
#             ),
#             dict(
#                 user=self.roles_contexts[
#                     self.admin_role_same_level.id
#                 ]['user_mother'],
#                 perimeter=self.mother_perim,
#                 expected=[self.pseudo_anonymised_data_role,
#                           self.nominative_data_role,
#                           self.full_data_access_role]
#             ),
#             dict(
#                 user=self.roles_contexts[
#                     self.admin_role_inf_level.id
#                 ]['user_mother'],
#                 perimeter=self.child_perim,
#                 expected=[self.pseudo_anonymised_data_role,
#                           self.nominative_data_role,
#                           self.full_data_access_role]
#             ),
#             dict(
#                 user=self.roles_contexts[
#                     self.admin_role_inf_level.id
#                 ]['user_mother'],
#                 perimeter=self.mother_perim,
#                 expected=[]
#             ),
#         ]
#         [self.check_list_role(
#             get_assignable_roles_on_perimeter(
#                 c['user'].pk, c['perimeter'].id
#             ), c['expected']) for c in cases]
#
#     def test_get_specific_roles(self):
#         non_roles = [*self.non_admin_roles,
#                      *self.non_admin_manager_roles,
#                      *self.non_data_acc_roles]
#         cases = [
#             dict(
#                 key="MAIN_ADMIN",
#                 type=RoleType.MAIN_ADMIN,
#                 expected=dict(inf_level=[
#                     self.main_admin_role,
#                     self.edit_role_admin_role,
#                     self.full_admin_manager_role,
#                     *[r for r in non_roles if r.right_full_admin]
#                 ], same_level=[
#                     self.main_admin_role,
#                     self.edit_role_admin_role,
#                     self.full_admin_manager_role,
#                     *[r for r in non_roles if r.right_full_admin]
#                 ]),
#             ),
#             dict(
#                 key="ADMIN_MANAGER",
#                 type=RoleType.ADMIN_MANAGER_READ,
#                 expected=dict(inf_level=[
#                     self.full_admin_manager_role,
#                     self.admin_manager_role_inf_level,
#                     self.admin_manager_role,
#                     *[r for r in non_roles
#                       if r.right_read_admin_accesses_inferior_levels]
#                 ], same_level=[
#                     self.full_admin_manager_role,
#                     self.admin_manager_role_same_level,
#                     self.admin_manager_role,
#                     *[r for r in non_roles
#                       if r.right_read_admin_accesses_same_level]
#                 ]),
#             ),
#             dict(
#                 key="ADMIN",
#                 type=RoleType.ADMIN_READ,
#                 expected=dict(inf_level=[
#                     self.full_admin_role,
#                     self.admin_role_inf_level,
#                     self.admin_role,
#                     *[r for r in non_roles
#                       if r.right_read_data_accesses_inferior_levels]
#                 ], same_level=[
#                     self.full_admin_role,
#                     self.admin_role_same_level,
#                     self.admin_role,
#                     *[r for r in non_roles
#                       if r.right_read_data_accesses_same_level]
#                 ]),
#             ),
#             dict(
#                 key="DATA_ACCESS",
#                 type=RoleType.DATA_ACCESS,
#                 expected=dict(inf_level=[
#                     self.full_data_access_role,
#                     self.pseudo_anonymised_data_role,
#                     self.nominative_data_role,
#                     *[r for r in non_roles
#                       if r.right_read_patient_nominative
#                       or r.right_read_patient_pseudonymized
#                       ]
#                 ], same_level=[
#                     self.full_data_access_role,
#                     self.pseudo_anonymised_data_role,
#                     self.nominative_data_role,
#                     *[r for r in non_roles
#                       if r.right_read_patient_nominative
#                       or r.right_read_patient_pseudonymized
#                       ]
#                 ]),
#             ),
#             dict(
#                 key="MANAGING_ACCESS",
#                 type=RoleType.MANAGING_ACCESS,
#                 expected=dict(inf_level=[
#                     self.admin_role, self.main_admin_role,
#                     self.edit_role_admin_role,
#                     self.admin_manager_role_inf_level,
#                     self.admin_role_inf_level,
#                     self.admin_manager_role, self.full_admin_role,
#                     self.full_admin_manager_role,
#                     *[r for r in non_roles
#                       if r.right_manage_admin_accesses_inferior_levels
#                       or r.right_manage_data_accesses_inferior_levels
#                       or r.right_full_admin]
#                 ], same_level=[
#                     self.admin_role, self.main_admin_role,
#                     self.edit_role_admin_role,
#                     self.admin_manager_role_same_level,
#                     self.admin_role_same_level,
#                     self.admin_manager_role, self.full_admin_role,
#                     self.full_admin_manager_role,
#                     *[r for r in non_roles
#                       if r.right_manage_admin_accesses_same_level
#                       or r.right_full_admin
#                       or r.right_manage_data_accesses_same_level]
#                 ]),
#             ),
#             dict(
#                 key="MANAGING_CSV_EXPORT",
#                 type=RoleType.MANAGING_CSV_EXPORT,
#                 expected=dict(inf_level=[
#                 ], same_level=[
#                 ]),
#             ),
#             dict(
#                 key="MANAGING_CSV_EXPORT_REVIEW",
#                 type=RoleType.MANAGING_CSV_EXPORT_REVIEW,
#                 expected=dict(inf_level=[
#                 ], same_level=[
#                 ]),
#             ),
#             dict(
#                 key="MANAGING_JUPYTER_TRANSFER",
#                 type=RoleType.MANAGING_JUPYTER_TRANSFER,
#                 expected=dict(inf_level=[
#                 ], same_level=[
#                 ]),
#             ),
#             dict(
#                 key="MANAGING_JUPYTER_TRANSFER_REVIEW",
#                 type=RoleType.MANAGING_JUPYTER_TRANSFER_REVIEW,
#                 expected=dict(inf_level=[
#                 ], same_level=[
#                 ]),
#             ),
#         ]
#         [self.check_list_role(
#             [
#                 Role.objects.get(id=i)
#                 for i in get_specific_roles(c['type'])[0]
#             ],
#             c['expected']['inf_level'],
#             c['key'] + "-inf"
#         )
#          and self.check_list_role(
#             [
#                 Role.objects.get(id=i)
#                 for i in get_specific_roles(c['type'])[1]
#             ],
#             c['expected']['same_level'],
#             c['key'] + "-same"
#         )
#          for c in cases]
