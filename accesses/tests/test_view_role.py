from django.db import IntegrityError
from rest_framework import status

from accesses.models import Role, Access
from accesses.services.shared import all_rights
from accesses.tests.base import AccessesAppTestsBase
from accesses.views import RoleViewSet
from admin_cohort.tools.tests_tools import new_user_and_profile, CreateCase, CaseRetrieveFilter, PatchCase, ListCase

ALL_FALSY_RIGHTS = {right.name: False for right in all_rights}

role_full_admin_data = {**{right.name: True for right in all_rights}, "name": "FULL ADMIN"}

role_admin_accesses_manager_data = {**ALL_FALSY_RIGHTS,
                                    "name": "ADMIN ACCESSES MANAGER",
                                    "right_manage_roles": True,
                                    "right_read_roles": True,
                                    "right_manage_admin_accesses_same_level": True,
                                    "right_read_admin_accesses_same_level": True,
                                    "right_manage_admin_accesses_inferior_levels": True,
                                    "right_read_admin_accesses_inferior_levels": True}

role_data_accesses_manager_data = {**ALL_FALSY_RIGHTS,
                                   "name": "DATA ACCESSES MANAGER",
                                   # "right_manage_roles": True,                todo: review roles requirements to be managed   /!\
                                   # "right_read_roles": True,
                                   "right_manage_data_accesses_same_level": True,
                                   "right_read_data_accesses_same_level": True,
                                   "right_manage_data_accesses_inferior_levels": True,
                                   "right_read_data_accesses_inferior_levels": True}

role_nomi_reader_nomi_csv_exporter_data = {**ALL_FALSY_RIGHTS,
                                           "name": "DATA NOMI READER + CSV EXPORTER",
                                           "right_manage_roles": True,
                                           "right_read_roles": True,
                                           "right_read_patient_nominative": True,
                                           "right_export_csv_nominative": True}

role_roles_manager_data = {**ALL_FALSY_RIGHTS,
                           "name": "ROLES MANAGER",
                           "right_manage_roles": True,
                           "right_read_roles": True}

# todo: suggestion: remove right_manage/read_roles
#       only full_admin can manage roles on Portail
#       make roles available for all users to see on Portail
6+

class RoleRetrieveFilter(CaseRetrieveFilter):

    def __init__(self, name: str, exclude: dict = None):
        self.name = name
        super().__init__(exclude=exclude)


class RoleViewTests(AccessesAppTestsBase):
    objects_url = "/roles/"
    retrieve_view = RoleViewSet.as_view({'get': 'retrieve'})
    list_view = RoleViewSet.as_view({'get': 'list'})
    create_view = RoleViewSet.as_view({'post': 'create'})
    delete_view = RoleViewSet.as_view({'delete': 'destroy'})
    update_view = RoleViewSet.as_view({'patch': 'partial_update'})
    assignable_view = RoleViewSet.as_view(actions={'get': 'assignable'})
    model = Role
    model_objects = Role.objects
    model_fields = Role._meta.fields

    def setUp(self):
        super().setUp()
        # roles for testing the `assignable` view
        self.role_full_admin = Role.objects.create(**role_full_admin_data)
        self.role_admin_accesses_manager = Role.objects.create(**role_admin_accesses_manager_data)
        self.role_data_accesses_manager = Role.objects.create(**role_data_accesses_manager_data)
        self.role_nomi_reader_nomi_csv_exporter = Role.objects.create(**role_nomi_reader_nomi_csv_exporter_data)
        self.role_roles_manager = Role.objects.create(**role_roles_manager_data)

        self.user_roles_manager, self.profile = new_user_and_profile(firstname="User",
                                                                     lastname="CAN MANAGE ROLES",
                                                                     email="user.who_can_manage_roles@aphp.fr")
        self.roles_manager_access = Access.objects.create(profile=self.profile,
                                                          role=self.role_roles_manager,
                                                          perimeter=self.aphp)
        self.user_full_admin_on_aphp, self.profile_full_admin_on_aphp = new_user_and_profile(firstname="Full",
                                                                                             lastname="ADMIN",
                                                                                             email="user.full_admin@aphp.fr")
        Access.objects.create(profile=self.profile_full_admin_on_aphp, role=self.role_full_admin, perimeter=self.aphp)

        self.all_roles = [self.role_full_admin,
                          self.role_admin_accesses_manager,
                          self.role_data_accesses_manager,
                          self.role_nomi_reader_nomi_csv_exporter,
                          self.role_roles_manager]

    def test_role_unique_name(self):
        data = {**ALL_FALSY_RIGHTS,
                "name": "CSV EXPORTER NOMI",
                "right_export_csv_nominative": True,
                }
        r = Role.objects.create(**data)
        self.assertIsNotNone(r)
        with self.assertRaises(IntegrityError):
            Role.objects.create(**{**data, "right_read_users": True})

    def test_duplicated_name_as_a_deleted_role(self):
        data = {**ALL_FALSY_RIGHTS,
                "name": "CSV EXPORTER NOMI",
                "right_export_csv_nominative": True,
                }
        r = Role.objects.create(**data)
        self.assertIsNotNone(r)
        r.delete()
        self.assertIsNotNone(r.delete_datetime)
        try:
            Role.objects.create(**{**data, "right_read_users": True})
        except IntegrityError:
            self.fail("Must be able to create a role having the same name as a previously deleted role")

    def test_unique_combination_of_rights(self):
        data = {**ALL_FALSY_RIGHTS,
                "name": "JUPYTER EXPORTER",
                "right_export_jupyter_nominative": True,
                "right_export_jupyter_pseudonymized": True,
                }
        r = Role.objects.create(**data)
        self.assertIsNotNone(r)
        with self.assertRaises(IntegrityError):
            Role.objects.create(**{**data, "name": "DIFFERENT NAME, SAME RIGHTS!"})

    def test_duplicated_combination_of_rights_as_a_deleted_role(self):
        data = {**ALL_FALSY_RIGHTS,
                "name": "JUPYTER EXPORTER",
                "right_export_jupyter_nominative": True,
                "right_export_jupyter_pseudonymized": True,
                }
        r = Role.objects.create(**data)
        self.assertIsNotNone(r)
        r.delete()
        self.assertIsNotNone(r.delete_datetime)
        try:
            Role.objects.create(**{**data, "name": "DIFFERENT NAME, SAME RIGHTS!"})
        except IntegrityError:
            self.fail("Must be able to create a role with same rights combination as a deleted role")

    def test_successfully_creating_role(self):
        data = {**ALL_FALSY_RIGHTS,
                "name": "DATA READER NOMI",
                "right_read_patient_nominative": True
                }
        case = CreateCase(data=data,
                          retrieve_filter=RoleRetrieveFilter(name="DATA READER NOMI"),
                          user=self.user_roles_manager,
                          status=status.HTTP_201_CREATED,
                          success=True)
        self.check_create_case(case)

    def test_error_creating_role_with_inconsistent_rights(self):
        role_name = "DATA READER PSEUDO & EXPORT NOMI"
        data = {**ALL_FALSY_RIGHTS,
                "name": role_name,
                "right_read_patient_pseudonymized": True,
                "right_export_csv_nominative": True
                }
        case = CreateCase(data=data,
                          retrieve_filter=RoleRetrieveFilter(name=role_name),
                          user=self.user_roles_manager,
                          status=status.HTTP_400_BAD_REQUEST,
                          success=False)
        self.check_create_case(case)

    def test_successfully_patch_role(self):
        initial_data = {**ALL_FALSY_RIGHTS,
                        "name": "USERS & LOGS READER",
                        "right_read_users": True,
                        "right_read_logs": True
                        }
        patch_data = {"name": "USERS MANAGER & LOGS READER",
                      "right_manage_users": True
                      }
        case = PatchCase(initial_data=initial_data,
                         data_to_update=patch_data,
                         user=self.user_roles_manager,
                         status=status.HTTP_200_OK,
                         success=True)
        self.check_patch_case(case)

    def test_patch_role_with_inconsistent_rights(self):
        initial_data = {**ALL_FALSY_RIGHTS,
                        "name": "DATA READER PSEUDO & EXPORT PSEUDO",
                        "right_read_patient_pseudonymized": True,
                        "right_export_csv_pseudonymized": True
                        }
        patch_data = {"name": "DATA READER PSEUDO & EXPORT NOMI",
                      "right_read_patient_pseudonymized": True,
                      "right_export_csv_nominative": True
                      }
        case = PatchCase(initial_data=initial_data,
                         data_to_update=patch_data,
                         user=self.user_roles_manager,
                         status=status.HTTP_400_BAD_REQUEST,
                         success=False)
        self.check_patch_case(case)

    def test_get_assignable_roles_missing_perimeter_id(self):
        case = ListCase(to_find=["Does not matter"],
                        user=self.user_roles_manager,
                        status=status.HTTP_400_BAD_REQUEST,
                        success=False)
        self.check_get_paged_list_case(case, other_view=RoleViewTests.assignable_view)

    def test_get_assignable_roles_on_perimeter_APHP_as_full_admin_on_APHP(self):
        """
        expected behavior: return all roles
                                                    APHP
                         ____________________________|____________________________
                        |                           |                           |
                       P0                          P1                          P2
             __________|__________          _______|_______          __________|__________
            |         |         |          |             |          |         |         |
           P3        P4       P5          P6            P7       P8          P9       P10
               ______|_______                                                    ______|_______
              |            |                                                    |            |
             P1          P12                                                  P13          P14
        """
        case = ListCase(params={"perimeter_id": self.aphp.id},
                        to_find=self.all_roles,
                        user=self.user_full_admin_on_aphp,
                        status=status.HTTP_200_OK,
                        success=True)
        self.check_get_paged_list_case(case, other_view=RoleViewTests.assignable_view)

    def test_get_assignable_roles_on_any_child_perimeter_of_APHP_as_full_admin_on_APHP(self):
        # according to the hierarchy above, target perimeters for ex: P5, P7 and P13
        # expected behavior: return all roles
        cases = [ListCase(title="get assignable role on perimeter P5",
                          params={"perimeter_id": self.p5.id},
                          to_find=self.all_roles,
                          user=self.user_full_admin_on_aphp,
                          status=status.HTTP_200_OK,
                          success=True),
                 ListCase(title="get assignable role on perimeter P7",
                          params={"perimeter_id": self.p7.id},
                          to_find=self.all_roles,
                          user=self.user_full_admin_on_aphp,
                          status=status.HTTP_200_OK,
                          success=True),
                 ListCase(title="get assignable role on perimeter P13",
                          params={"perimeter_id": self.p13.id},
                          to_find=self.all_roles,
                          user=self.user_full_admin_on_aphp,
                          status=status.HTTP_200_OK,
                          success=True)]
        for case in cases:
            self.check_get_paged_list_case(case, other_view=RoleViewTests.assignable_view)

    def test_get_assignable_roles_on_perimeter_P0_as_admin_accesses_manager_on_APHP(self):
        # according to the hierarchy above
        # expected behavior: return `role_data_accesses_manager` only
        user_admin_accesses_manager_on_aphp, profile = new_user_and_profile(firstname="AdministrationAccesses",
                                                                            lastname="MANAGER",
                                                                            email="user.admin_acc_manager@aphp.fr")
        Access.objects.create(profile=profile, role=self.role_admin_accesses_manager, perimeter=self.aphp)
        case = ListCase(params={"perimeter_id": self.p0.id},
                        to_find=[self.role_data_accesses_manager],
                        user=user_admin_accesses_manager_on_aphp,
                        status=status.HTTP_200_OK,
                        success=True)
        self.check_get_paged_list_case(case, other_view=RoleViewTests.assignable_view)

    def test_get_assignable_roles_on_perimeter_P0_as_admin_accesses_manager_on_P0(self):
        ...

    def test_get_assignable_roles_on_perimeter_P0_as_admin_accesses_manager_on_P4(self):
        ...
