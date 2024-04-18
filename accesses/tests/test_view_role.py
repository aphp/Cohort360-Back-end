from django.db import IntegrityError
from rest_framework import status

from accesses.models import Role, Access
from accesses.tests.base import AccessesAppTestsBase, ALL_FALSY_RIGHTS
from accesses.views import RoleViewSet
from admin_cohort.tests.tests_tools import new_user_and_profile, CreateCase, CaseRetrieveFilter, PatchCase, ListCase


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
    assignable_view = RoleViewSet.as_view(actions={'get': 'get_assignable_roles'})
    model = Role
    model_objects = Role.objects
    model_fields = Role._meta.fields

    def setUp(self):
        super().setUp()
        self.user_full_admin_on_aphp, profile_full_admin_on_aphp = new_user_and_profile()
        Access.objects.create(profile=profile_full_admin_on_aphp, role=self.role_full_admin, perimeter=self.aphp)

        self.user_non_full_admin, profile = new_user_and_profile()
        Access.objects.create(profile=profile, role=self.role_admin_accesses_manager, perimeter=self.aphp)

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
        role_name = "DATA READER NOMI + LOGS READER"
        data = {**ALL_FALSY_RIGHTS,
                "name": role_name,
                "right_read_patient_nominative": True,
                "right_read_logs": True
                }
        case = CreateCase(data=data,
                          retrieve_filter=RoleRetrieveFilter(name=role_name),
                          user=self.user_full_admin_on_aphp,
                          status=status.HTTP_201_CREATED,
                          success=True)
        self.check_create_case(case)

    def test_error_creating_role_as_non_full_admin(self):
        role_name = "DATA READER NOMI + SEARCH BY IPP"
        data = {**ALL_FALSY_RIGHTS,
                "name": role_name,
                "right_read_patient_nominative": True,
                "right_search_patients_by_ipp": True
                }
        case = CreateCase(data=data,
                          retrieve_filter=RoleRetrieveFilter(name=role_name),
                          user=self.user_non_full_admin,
                          status=status.HTTP_403_FORBIDDEN,
                          success=False)
        self.check_create_case(case)

    def test_error_creating_role_with_inconsistent_rights(self):
        cases_data = [{**ALL_FALSY_RIGHTS,
                       "name": "DATA READER PSEUDO & EXPORT NOMI",
                       "right_read_patient_pseudonymized": True,
                       "right_export_csv_nominative": True
                       },
                      {**ALL_FALSY_RIGHTS,
                       "name": "FULL ADMIN WITH SOME FALSY RIGHTS",
                       "right_full_admin": True,
                       "right_manage_users": True,
                       "right_read_logs": True
                       },
                      {**ALL_FALSY_RIGHTS,
                       "name": "ADMINISTRATION ACCESSES MANAGER WITHOUT USERS MANAGEMENT",
                       "right_manage_admin_accesses_same_level": True,
                       "right_read_admin_accesses_same_level": True,
                       "right_manage_admin_accesses_inferior_levels": True,
                       "right_read_admin_accesses_inferior_levels": True
                       },
                      {**ALL_FALSY_RIGHTS,
                       "name": "EXPORT ACCESSES MANAGER WITHOUT USERS MANAGEMENT",
                       "right_manage_export_csv_accesses": True,
                       "right_manage_export_jupyter_accesses": True
                       }]
        for d in cases_data:
            self.check_create_case(CreateCase(data=d,
                                              retrieve_filter=RoleRetrieveFilter(name=d["name"]),
                                              user=self.user_full_admin_on_aphp,
                                              status=status.HTTP_400_BAD_REQUEST,
                                              success=False))

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
                         user=self.user_full_admin_on_aphp,
                         status=status.HTTP_200_OK,
                         success=True)
        self.check_patch_case(case)

    def test_error_patching_role_as_non_full_admin(self):
        case = PatchCase(initial_data={},
                         data_to_update={},
                         user=self.user_non_full_admin,
                         status=status.HTTP_403_FORBIDDEN,
                         success=False)
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
                         user=self.user_full_admin_on_aphp,
                         status=status.HTTP_400_BAD_REQUEST,
                         success=False)
        self.check_patch_case(case)

    def test_get_assignable_roles_missing_perimeter_id(self):
        case = ListCase(to_find=["Does not matter"],
                        user=self.user_full_admin_on_aphp,
                        status=status.HTTP_400_BAD_REQUEST,
                        success=False)
        self.check_list_case(case, other_view=RoleViewTests.assignable_view)

    def test_get_assignable_roles_on_perimeter_APHP_as_full_admin_on_APHP(self):
        """
        expected behavior: return all roles
                                                            APHP
                                 ____________________________|____________________________
                                |                           |                            |
                               P0                          P1                           P2
                     __________|__________          _______|_______           __________|__________
                    |         |          |         |              |          |          |         |
                   P3        P4       P5          P6             P7         P8         P9        P10
                       ______|_______                                                       ______|_______
                      |             |                                                      |             |
                     P1           P12                                                     P13           P14
        """
        case = ListCase(params={"perimeter_id": self.aphp.id},
                        to_find=Role.objects.all(),
                        user=self.user_full_admin_on_aphp,
                        status=status.HTTP_200_OK,
                        success=True)
        self.check_list_case(case, other_view=RoleViewTests.assignable_view)

    def test_get_assignable_roles_on_any_child_perimeter_of_APHP_as_full_admin_on_APHP(self):
        # according to the hierarchy above, target perimeters for ex: P5, P7 and P13
        # expected behavior: return all roles
        all_roles = Role.objects.all()
        cases = [ListCase(title="get assignable role on perimeter P5",
                          params={"perimeter_id": self.p5.id},
                          to_find=all_roles,
                          user=self.user_full_admin_on_aphp,
                          status=status.HTTP_200_OK,
                          success=True),
                 ListCase(title="get assignable role on perimeter P7",
                          params={"perimeter_id": self.p7.id},
                          to_find=all_roles,
                          user=self.user_full_admin_on_aphp,
                          status=status.HTTP_200_OK,
                          success=True),
                 ListCase(title="get assignable role on perimeter P13",
                          params={"perimeter_id": self.p13.id},
                          to_find=all_roles,
                          user=self.user_full_admin_on_aphp,
                          status=status.HTTP_200_OK,
                          success=True)]
        for case in cases:
            self.check_list_case(case, other_view=RoleViewTests.assignable_view)

    def test_get_assignable_roles_on_perimeter_P0_as_admin_accesses_manager_on_APHP(self):
        # expected behavior: return `role_data_accesses_manager` and `role_data_accesses_manager_inf_levels`
        user_admin_accesses_manager_on_aphp, profile = new_user_and_profile()
        Access.objects.create(profile=profile, role=self.role_admin_accesses_manager, perimeter=self.aphp)
        to_find = [self.role_data_accesses_manager,
                   self.role_data_accesses_manager_inf_levels]
        case = ListCase(params={"perimeter_id": self.p0.id},
                        to_find=to_find,
                        user=user_admin_accesses_manager_on_aphp,
                        status=status.HTTP_200_OK,
                        success=True)
        self.check_list_case(case, other_view=RoleViewTests.assignable_view)

    def test_get_assignable_roles_on_perimeter_P0_as_admin_accesses_manager_on_P0(self):
        # expected behavior: return `role_data_accesses_manager` only
        user_admin_accesses_manager_on_p0, profile = new_user_and_profile()
        Access.objects.create(profile=profile, role=self.role_admin_accesses_manager, perimeter=self.p0)
        to_find = [self.role_data_accesses_manager,
                   self.role_data_accesses_manager_inf_levels]
        case = ListCase(params={"perimeter_id": self.p0.id},
                        to_find=to_find,
                        user=user_admin_accesses_manager_on_p0,
                        status=status.HTTP_200_OK,
                        success=True)
        self.check_list_case(case, other_view=RoleViewTests.assignable_view)

    def test_get_assignable_roles_on_perimeter_P0_as_admin_accesses_manager_on_P4(self):
        # expected behavior: return no roles, HTTP 200 OK
        user_admin_accesses_manager_on_p4, profile = new_user_and_profile()
        Access.objects.create(profile=profile, role=self.role_admin_accesses_manager, perimeter=self.p4)
        case = ListCase(params={"perimeter_id": self.p0.id},
                        to_find=[],
                        user=user_admin_accesses_manager_on_p4,
                        status=status.HTTP_200_OK,
                        success=False)
        self.check_list_case(case, other_view=RoleViewTests.assignable_view)
