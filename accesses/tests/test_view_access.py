import time
from datetime import timedelta

from django.db.models import Q
from django.utils import timezone
from rest_framework import status

from accesses.models import Access, Role
from accesses.tests.base import AccessesAppTestsBase, ALL_FALSY_RIGHTS
from accesses.views import AccessViewSet
from admin_cohort.settings import MIN_DEFAULT_END_DATE_OFFSET_IN_DAYS
from admin_cohort.tools.tests_tools import CaseRetrieveFilter, CreateCase, new_user_and_profile, PatchCase, ListCase


def create_accesses_for_user_x(roles, perimeters):
    user_x, profile_x = new_user_and_profile(email="user_x@aphp.fr")
    for role, perimeter in zip(roles, perimeters):
        Access.objects.create(profile=profile_x, role=role, perimeter=perimeter)
    return user_x, profile_x


class AccessesRetrieveFilter(CaseRetrieveFilter):
    def __init__(self, perimeter_id: int = None, role_id: int = None, profile_id: int = None, **kwargs):
        self.perimeter_id = perimeter_id
        self.role_id = role_id or kwargs.get('role_id')
        self.profile_id = profile_id or kwargs.get('profile_id')
        super().__init__(**kwargs)


class AccessViewTests(AccessesAppTestsBase):
    objects_url = "/accesses/"
    retrieve_view = AccessViewSet.as_view({'get': 'retrieve'})
    list_view = AccessViewSet.as_view({'get': 'list'})
    create_view = AccessViewSet.as_view({'post': 'create'})
    delete_view = AccessViewSet.as_view({'delete': 'destroy'})
    update_view = AccessViewSet.as_view({'patch': 'partial_update'})
    close_view = AccessViewSet.as_view(actions={'patch': 'close'})
    model = Access
    model_objects = Access.objects
    model_fields = Access._meta.fields

    def setUp(self):
        super().setUp()
        self.user_data_accesses_manager_on_aphp, profile1 = new_user_and_profile(email="user_data_accesses_manager@aphp.fr")
        Access.objects.create(profile=profile1, role=self.role_data_accesses_manager, perimeter=self.aphp)

        self.user_non_accesses_manager, profile2 = new_user_and_profile(email="user_non_accesses_manager@aphp.fr")
        Access.objects.create(profile=profile2, role=self.role_data_reader_nomi_csv_exporter_nomi, perimeter=self.aphp)

        _, profile3 = new_user_and_profile(email="user_01@aphp.fr")
        basic_role = Role.objects.create(**{**ALL_FALSY_RIGHTS,
                                            "name": "DATA NOMI READER",
                                            "right_read_patient_nominative": True})
        self.basic_access_data = {"profile_id": profile3.id,
                                  "role_id": basic_role.id,
                                  "perimeter_id": self.aphp.id
                                  }
        self.basic_retrieve_filter = AccessesRetrieveFilter(**self.basic_access_data)

    def check_close_case(self, close_case: PatchCase):
        self.check_patch_case(close_case, other_view=AccessViewTests.close_view)
        close_case.initial_data.pop("end_datetime")
        access = Access.objects.get(Q(**close_case.initial_data))
        if close_case.success:
            self.assertFalse(access.is_valid)

    def test_successfully_create_access(self):
        data = {**self.basic_access_data,
                "start_datetime": timezone.now(),
                "end_datetime": timezone.now() + timedelta(days=10)
                }
        case = CreateCase(data=data,
                          user=self.user_data_accesses_manager_on_aphp,
                          status=status.HTTP_201_CREATED,
                          success=True,
                          retrieve_filter=self.basic_retrieve_filter)
        self.check_create_case(case)

    def test_successfully_create_access_with_empty_end_datetime(self):
        data = {**self.basic_access_data,
                "start_datetime": timezone.now()
                }
        case = CreateCase(data=data,
                          user=self.user_data_accesses_manager_on_aphp,
                          status=status.HTTP_201_CREATED,
                          success=True,
                          retrieve_filter=self.basic_retrieve_filter)
        self.check_create_case(case)
        access = Access.objects.get(Q(**data))
        expected_end_datetime = data["start_datetime"] + timedelta(days=MIN_DEFAULT_END_DATE_OFFSET_IN_DAYS)
        self.assertEqual(expected_end_datetime, access.end_datetime)

    def test_error_create_access_with_past_start_end_datetime(self):
        past_datetime = timezone.now() - timedelta(days=1)
        data = {**self.basic_access_data,
                "start_datetime": past_datetime}
        case_with_past_start_datetime = CreateCase(data=data,
                                                   user=self.user_data_accesses_manager_on_aphp,
                                                   status=status.HTTP_400_BAD_REQUEST,
                                                   success=False,
                                                   retrieve_filter=self.basic_retrieve_filter)
        case_with_past_end_datetime = case_with_past_start_datetime.clone(data={**data,
                                                                                "start_datetime": timezone.now(),
                                                                                "end_datetime": past_datetime})
        self.check_create_case(case_with_past_start_datetime)
        self.check_create_case(case_with_past_end_datetime)

    def test_error_create_access_missing_any_of_role_perimeter_profile(self):
        data1, data2, data3 = (self.basic_access_data.copy() for _ in range(3))
        data1.pop("role_id")
        data2.pop("profile_id")
        data3.pop("perimeter_id")

        for data in (data1, data2, data3):
            self.check_create_case(CreateCase(data=data,
                                              user=self.user_data_accesses_manager_on_aphp,
                                              status=status.HTTP_400_BAD_REQUEST,
                                              success=False,
                                              retrieve_filter=self.basic_retrieve_filter))

    def test_error_create_access_as_non_accesses_manager(self):
        self.check_create_case(CreateCase(data=self.basic_access_data,
                                          user=self.user_non_accesses_manager,
                                          status=status.HTTP_403_FORBIDDEN,
                                          success=False,
                                          retrieve_filter=self.basic_retrieve_filter))

    def test_successfully_close_access(self):
        initial_data = {**self.basic_access_data,
                        "start_datetime": timezone.now(),
                        "end_datetime": timezone.now() + timedelta(weeks=1)
                        }
        case = PatchCase(initial_data=initial_data,
                         data_to_update={},
                         user=self.user_data_accesses_manager_on_aphp,
                         status=status.HTTP_200_OK,
                         success=True)
        self.check_close_case(case)

    def test_error_close_a_future_access(self):
        initial_data = {**self.basic_access_data,
                        "start_datetime": timezone.now() + timedelta(weeks=1),
                        "end_datetime": timezone.now() + timedelta(weeks=2)
                        }
        case = PatchCase(initial_data=initial_data,
                         data_to_update={},
                         user=self.user_data_accesses_manager_on_aphp,
                         status=status.HTTP_400_BAD_REQUEST,
                         success=False)
        self.check_close_case(case)

    def test_error_close_an_already_closed_access(self):
        initial_data = {**self.basic_access_data,
                        "start_datetime": timezone.now(),
                        "end_datetime": timezone.now() + timedelta(seconds=1)
                        }
        time.sleep(5)
        case = PatchCase(initial_data=initial_data,
                         data_to_update={},
                         user=self.user_data_accesses_manager_on_aphp,
                         status=status.HTTP_400_BAD_REQUEST,
                         success=False)
        self.check_close_case(case)

    def test_successfully_patch_access(self):
        initial_data = {**self.basic_access_data,
                        "start_datetime": timezone.now(),
                        "end_datetime": timezone.now() + timedelta(weeks=1)
                        }
        self.check_patch_case(PatchCase(initial_data=initial_data,
                                        data_to_update={"end_datetime": timezone.now() + timedelta(weeks=3)},
                                        user=self.user_data_accesses_manager_on_aphp,
                                        status=status.HTTP_200_OK,
                                        success=True))

    def test_error_patch_access_with_past_end_datetime(self):
        initial_data = {**self.basic_access_data,
                        "start_datetime": timezone.now(),
                        "end_datetime": timezone.now() + timedelta(weeks=1)
                        }
        self.check_patch_case(PatchCase(initial_data=initial_data,
                                        data_to_update={"end_datetime": timezone.now() - timedelta(weeks=3)},
                                        user=self.user_data_accesses_manager_on_aphp,
                                        status=status.HTTP_400_BAD_REQUEST,
                                        success=False))

    def test_successfully_patch_a_future_access(self):
        initial_data = {**self.basic_access_data,
                        "start_datetime": timezone.now() + timedelta(weeks=1),
                        "end_datetime": timezone.now() + timedelta(weeks=2)
                        }
        shift_dates_one_week = {"start_datetime": timezone.now() + timedelta(weeks=3),
                                "end_datetime": timezone.now() + timedelta(weeks=4)
                                }
        self.check_patch_case(PatchCase(initial_data=initial_data,
                                        data_to_update=shift_dates_one_week,
                                        user=self.user_data_accesses_manager_on_aphp,
                                        status=status.HTTP_200_OK,
                                        success=True))

    def test_error_patch_a_future_access_missing_dates(self):
        initial_data = {**self.basic_access_data,
                        "start_datetime": timezone.now() + timedelta(weeks=1),
                        "end_datetime": timezone.now() + timedelta(weeks=2)
                        }
        self.check_patch_case(PatchCase(initial_data=initial_data,
                                        data_to_update={},
                                        user=self.user_data_accesses_manager_on_aphp,
                                        status=status.HTTP_400_BAD_REQUEST,
                                        success=False))

    def test_error_patch_a_future_access_with_wrong_dates(self):
        initial_data = {**self.basic_access_data,
                        "start_datetime": timezone.now() + timedelta(weeks=1),
                        "end_datetime": timezone.now() + timedelta(weeks=2)
                        }
        swap_dates = {"start_datetime": initial_data["end_datetime"],
                      "end_datetime": initial_data["start_datetime"]
                      }
        self.check_patch_case(PatchCase(initial_data=initial_data,
                                        data_to_update=swap_dates,
                                        user=self.user_data_accesses_manager_on_aphp,
                                        status=status.HTTP_400_BAD_REQUEST,
                                        success=False))

    def test_error_patch_access_with_fields_other_than_dates(self):
        initial_data = {**self.basic_access_data,
                        "start_datetime": timezone.now() + timedelta(weeks=1),
                        "end_datetime": timezone.now() + timedelta(weeks=2)
                        }
        update_perimeter = {"perimeter_id": self.p7.id}
        self.check_patch_case(PatchCase(initial_data=initial_data,
                                        data_to_update=update_perimeter,
                                        user=self.user_data_accesses_manager_on_aphp,
                                        status=status.HTTP_400_BAD_REQUEST,
                                        success=False))

    def test_error_patch_access_as_non_accesses_manager_user(self):
        initial_data = {**self.basic_access_data,
                        "start_datetime": timezone.now(),
                        "end_datetime": timezone.now() + timedelta(weeks=1)
                        }
        self.check_patch_case(PatchCase(initial_data=initial_data,
                                        data_to_update={"end_datetime": timezone.now() + timedelta(weeks=3)},
                                        user=self.user_non_accesses_manager,
                                        status=status.HTTP_403_FORBIDDEN,
                                        success=False))

    def test_list_accesses_of_user_x_as_user_y(self):
        """                                         APHP
                         ____________________________|____________________________
                         |                           |                           |
                         P0                          P1                          P2
               __________|__________          _______|_______          __________|__________
               |         |         |          |             |          |         |         |
               P3        P4       P5          P6            P7       P8          P9       P10
                   ______|_______                                                    ______|_______
                   |            |                                                    |            |
                   P11         P12                                                  P13          P14

        with respect to this hierarchy,
        - User X has 3 valid accesses:
              P1:  data reader nomi
              P4:  admin accesses manager (on same level + inf levels)
              P10: data accesses manager (on same level + inf levels)
        - we create different accesses for User Y and test which of
          the User X's accesses he's allowed to read/manage
        """
        user_x, profile_x = create_accesses_for_user_x(roles=[self.role_data_reader_nomi_pseudo,
                                                              self.role_admin_accesses_manager,
                                                              self.role_data_accesses_manager],
                                                       perimeters=[self.p1, self.p4, self.p10])

        user_y, profile_y = new_user_and_profile(email="user_y@aphp.fr")

        def test_as_user_y_is_full_admin_on_aphp():
            Access.objects.create(profile=profile_y, role=self.role_full_admin, perimeter=self.aphp)
            case = ListCase(params={"profile_id": profile_x.id},
                            to_find=list(profile_x.accesses.all()),
                            user=user_y,
                            status=status.HTTP_200_OK,
                            success=True)
            resp_results = self.check_get_paged_list_case(case, yield_response_results=True)
            for access in resp_results:
                self.assertTrue(access.get("editable"))

        def test_as_user_y_is_admin_accesses_manager_on_aphp():
            # close full_admin access for user_y before creating new access
            profile_y.accesses.all().update(end_datetime=timezone.now())
            Access.objects.create(profile=profile_y, role=self.role_admin_accesses_manager, perimeter=self.aphp)

            case = ListCase(params={"profile_id": profile_x.id},
                            to_find=list(profile_x.accesses.filter(perimeter=self.p10)),
                            user=user_y,
                            status=status.HTTP_200_OK,
                            success=True)
            resp_results = self.check_get_paged_list_case(case, yield_response_results=True)
            for access in resp_results:
                self.assertTrue(access.get("editable"))

        def test_as_user_y_is_data_accesses_manager_on_aphp():
            # close previous accesses for user_y before creating new one
            profile_y.accesses.all().update(end_datetime=timezone.now())
            Access.objects.create(profile=profile_y, role=self.role_data_accesses_manager, perimeter=self.aphp)

            case = ListCase(params={"profile_id": profile_x.id},
                            to_find=list(profile_x.accesses.filter(perimeter=self.p1)),
                            user=user_y,
                            status=status.HTTP_200_OK,
                            success=True)
            resp_results = self.check_get_paged_list_case(case, yield_response_results=True)
            for access in resp_results:
                self.assertTrue(access.get("editable"))

        test_as_user_y_is_full_admin_on_aphp()
        test_as_user_y_is_admin_accesses_manager_on_aphp()
        test_as_user_y_is_data_accesses_manager_on_aphp()

    def test_list_accesses_on_perimeter_Px_for_user_y(self):
        ...
