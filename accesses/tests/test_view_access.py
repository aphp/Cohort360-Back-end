import time
from datetime import timedelta

from django.db.models import Q
from django.utils import timezone
from django.conf import settings

from rest_framework import status

from accesses.models import Access
from accesses.tests.base import AccessesAppTestsBase
from accesses.views import AccessViewSet
from admin_cohort.tests.tests_tools import CaseRetrieveFilter, CreateCase, new_user_and_profile, PatchCase, ListCase, DeleteCase


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
    get_my_accesses_view = AccessViewSet.as_view(actions={'get': 'get_my_accesses'})
    get_my_data_reading_rights_view = AccessViewSet.as_view(actions={'get': 'get_my_data_reading_rights'})
    model = Access
    model_objects = Access.objects
    model_fields = Access._meta.fields

    def setUp(self):
        super().setUp()
        self.user_data_accesses_manager_on_aphp, profile1 = new_user_and_profile()
        self.user_non_accesses_manager, profile2 = new_user_and_profile()
        Access.objects.create(profile=profile1,
                              role=self.role_data_accesses_manager,
                              perimeter=self.aphp,
                              start_datetime=timezone.now(),
                              end_datetime=timezone.now() + timedelta(weeks=1))
        Access.objects.create(profile=profile2,
                              role=self.role_data_reader_nomi_csv_exporter_nomi,
                              perimeter=self.aphp,
                              start_datetime=timezone.now(),
                              end_datetime=timezone.now() + timedelta(weeks=1))

        _, profile3 = new_user_and_profile()
        self.basic_access_data = {"profile_id": profile3.id,
                                  "role_id": self.role_data_reader_nomi.id,
                                  "perimeter_id": self.aphp.id
                                  }
        self.basic_retrieve_filter = AccessesRetrieveFilter(**self.basic_access_data)

    def check_close_case(self, close_case: PatchCase):
        self.check_patch_case(close_case, other_view=AccessViewTests.close_view)
        close_case.initial_data.pop("end_datetime")
        access = Access.objects.get(Q(**close_case.initial_data))
        if close_case.success:
            self.assertFalse(access.is_valid)

    def create_accesses_on_all_perimeters(self):
        _, regular_profile = new_user_and_profile()
        for perimeter in self.all_perimeters:
            Access.objects.create(profile=regular_profile,
                                  role=self.role_data_reader_nomi_pseudo,
                                  perimeter=perimeter,
                                  start_datetime=timezone.now(),
                                  end_datetime=timezone.now() + timedelta(weeks=1))

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
        expected_end_datetime = data["start_datetime"] + timedelta(days=settings.DEFAULT_ACCESS_VALIDITY_IN_DAYS)
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

    def test_delete_accesses(self):
        self.create_new_access_for_user(profile=self.profile_y, role=self.role_data_accesses_manager, perimeter=self.aphp)
        case_started_access = DeleteCase(data_to_delete=dict(perimeter=self.p5,
                                                             role=self.role_data_reader_nomi_pseudo,
                                                             profile=self.profile_y,
                                                             start_datetime=timezone.now() - timedelta(days=1),
                                                             end_datetime=timezone.now() + timedelta(days=10)),
                                         user=self.user_y,
                                         status=status.HTTP_400_BAD_REQUEST,
                                         success=False)
        case_future_access = DeleteCase(data_to_delete=dict(perimeter=self.p5,
                                                            role=self.role_data_reader_nomi_pseudo,
                                                            profile=self.profile_y,
                                                            start_datetime=timezone.now() + timedelta(days=1),
                                                            end_datetime=timezone.now() + timedelta(days=10)),
                                        user=self.user_y,
                                        status=status.HTTP_204_NO_CONTENT,
                                        success=True)
        self.check_delete_case(case_started_access)
        self.check_delete_case(case_future_access)

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

        - With respect to this hierarchy, User X has 3 valid accesses:
              P1:  data reader nomi
              P4:  admin accesses manager (on same level + inf levels)
              P10: data accesses manager (on same level + inf levels)
        - Create different accesses for User Y and test which of the User X's accesses he's allowed to read/manage
        """

        user_x, profile_x = new_user_and_profile()

        user_x_roles = [self.role_data_reader_nomi_pseudo, self.role_admin_accesses_manager, self.role_data_accesses_manager]
        user_x_perimeters = [self.p1, self.p4, self.p10]

        for r, p in zip(user_x_roles, user_x_perimeters):
            Access.objects.create(profile=profile_x,
                                  role=r,
                                  perimeter=p,
                                  start_datetime=timezone.now(),
                                  end_datetime=timezone.now() + timedelta(weeks=1))

        base_case = ListCase(params={"profile_id": profile_x.id},
                             to_find=[],
                             user=self.user_y,
                             status=status.HTTP_200_OK,
                             success=True)

        def test_as_user_y_is_full_admin_on_aphp():
            self.create_new_access_for_user(profile=self.profile_y, role=self.role_full_admin, perimeter=self.aphp)
            to_find = profile_x.accesses.all()
            resp_results = self.check_get_paged_list_case(base_case.clone(to_find=to_find),
                                                          yield_response_results=True)
            for access in resp_results:
                self.assertTrue(access.get("editable"))

        def test_as_user_y_is_admin_accesses_manager_on_aphp():
            self.create_new_access_for_user(profile=self.profile_y, role=self.role_admin_accesses_manager, perimeter=self.aphp)
            to_find = profile_x.accesses.filter(perimeter=self.p10)
            resp_results = self.check_get_paged_list_case(base_case.clone(to_find=to_find),
                                                          yield_response_results=True)
            for access in resp_results:
                self.assertTrue(access.get("editable"))

        def test_as_user_y_is_admin_accesses_reader_on_aphp():
            self.create_new_access_for_user(profile=self.profile_y, role=self.role_admin_accesses_reader, perimeter=self.aphp)
            to_find = profile_x.accesses.filter(perimeter=self.p10)
            resp_results = self.check_get_paged_list_case(base_case.clone(to_find=to_find),
                                                          yield_response_results=True)
            for access in resp_results:
                self.assertFalse(access.get("editable"))

        def test_as_user_y_is_data_accesses_manager_on_aphp():
            self.create_new_access_for_user(profile=self.profile_y, role=self.role_data_accesses_manager, perimeter=self.aphp)
            to_find = profile_x.accesses.filter(perimeter=self.p1)
            resp_results = self.check_get_paged_list_case(base_case.clone(to_find=to_find),
                                                          yield_response_results=True)
            for access in resp_results:
                self.assertTrue(access.get("editable"))

        test_as_user_y_is_full_admin_on_aphp()
        test_as_user_y_is_admin_accesses_manager_on_aphp()
        test_as_user_y_is_admin_accesses_reader_on_aphp()
        test_as_user_y_is_data_accesses_manager_on_aphp()

    def test_list_accesses_on_perimeter_P_for_user_y(self):

        self.create_accesses_on_all_perimeters()

        base_case = ListCase(params={},
                             to_find=[],
                             user=self.user_y,
                             status=status.HTTP_200_OK,
                             success=True)

        def test_list_accesses_on_p2_as_user_y_is_full_admin_on_aphp():
            self.create_new_access_for_user(profile=self.profile_y, role=self.role_full_admin, perimeter=self.aphp)
            target_perimeter_id = self.p2.id

            params_1 = {"perimeter_id": target_perimeter_id, "include_parents": "false"}
            to_find_1 = Access.objects.filter(Q(perimeter_id=target_perimeter_id))

            params_2 = {"perimeter_id": target_perimeter_id, "include_parents": "true"}
            to_find_2 = Access.objects.filter(Q(perimeter_id=target_perimeter_id)
                                              | Q(perimeter_id=self.aphp.id))

            case_1 = base_case.clone(params=params_1, to_find=to_find_1)
            case_2 = base_case.clone(params=params_2, to_find=to_find_2)

            for case in (case_1, case_2):
                self.check_get_paged_list_case(case=case)

        test_list_accesses_on_p2_as_user_y_is_full_admin_on_aphp()

    def test_successfully_get_my_accesses(self):
        self.create_new_access_for_user(profile=self.profile_y, role=self.role_data_accesses_manager, perimeter=self.p7)
        case = ListCase(params={},
                        to_find=self.profile_y.accesses.all(),
                        user=self.user_y,
                        status=status.HTTP_200_OK,
                        success=True)
        self.check_list_case(case, other_view=AccessViewTests.get_my_accesses_view)

    def test_successfully_get_my_valid_accesses_only(self):
        self.create_new_access_for_user(profile=self.profile_y, role=self.role_data_reader_nomi_pseudo, perimeter=self.p8)
        invalid_access_for_user_y = Access.objects.create(profile=self.profile_y,
                                                          role=self.role_data_reader_nomi_csv_exporter_nomi,
                                                          perimeter=self.p9,
                                                          start_datetime=timezone.now() - timedelta(days=2),
                                                          end_datetime=timezone.now() - timedelta(days=1))
        case = ListCase(params={},
                        to_find=self.profile_y.accesses.exclude(id=invalid_access_for_user_y.id),
                        user=self.user_y,
                        status=status.HTTP_200_OK,
                        success=True)
        self.check_list_case(case, other_view=AccessViewTests.get_my_accesses_view)

    def test_get_expiring_accesses(self):
        self.create_new_access_for_user(profile=self.profile_y, role=self.role_data_reader_nomi_pseudo, perimeter=self.p8)
        expiring_access_for_user_y = Access.objects.create(profile=self.profile_y,
                                                           role=self.role_data_reader_nomi_csv_exporter_nomi,
                                                           perimeter=self.p9,
                                                           start_datetime=timezone.now(),
                                                           end_datetime=timezone.now() +
                                                                        timedelta(days=settings.ACCESS_EXPIRY_FIRST_ALERT_IN_DAYS - 1))
        case_1 = ListCase(params={"expiring": "true"},
                          to_find=[expiring_access_for_user_y],
                          user=self.user_y,
                          status=status.HTTP_200_OK,
                          success=True)
        case_2 = case_1.clone(params={"expiring": "false"},
                              to_find=self.profile_y.accesses.all())
        for case in (case_1, case_2):
            self.check_list_case(case, other_view=AccessViewTests.get_my_accesses_view)

    def test_get_my_data_reading_rights(self):
        """                                                 APHP
                                 ____________________________|____________________________
                                 |                           |                           |
                                -P0-                        -P1-                         P2
                       __________|__________          _______|_______          __________|__________
                       |         |         |          |             |          |         |         |
                       P3        P4       P5          P6           -P7-      -P8-       P9        P10
                           ______|_______                                                    ______|_______
                           |            |                                                    |            |
                           P11        -P12-                                                 P13          P14
        """
        base_case = ListCase(params={},
                             to_find=[],
                             user=self.user_y,
                             status=status.HTTP_200_OK,
                             success=True)

        perimeters = [self.p0, self.p1, self.p7, self.p8, self.p12]
        roles = [self.role_data_reader_nomi_pseudo,
                 self.role_admin_accesses_reader,
                 self.role_jupyter_exporter_pseudo,
                 self.role_data_reader_nomi_csv_exporter_nomi,
                 self.role_search_by_ipp_and_search_opposed]

        for role, perimeter in zip(roles, perimeters):
            self.create_new_access_for_user(profile=self.profile_y, role=role, perimeter=perimeter, close_existing=False)

        target_perimeters_p0 = [self.p0.id]
        to_find_on_p0 = [dict(user_id=self.user_y.pk,
                              perimeter_id=self.p0.id,
                              right_read_patient_nominative=True,
                              right_read_patient_pseudonymized=True,
                              right_search_patients_by_ipp=True,
                              right_search_opposed_patients=True,
                              right_export_csv_nominative=True,
                              right_export_csv_pseudonymized=False,
                              right_export_jupyter_nominative=False,
                              right_export_jupyter_pseudonymized=True)]

        target_perimeters_p2 = [self.p2.id]
        to_find_on_p2 = []

        target_perimeters_p4_p10 = [self.p4.id, self.p10.id]
        to_find_on_p4_p10 = [dict(user_id=self.user_y.pk,
                                  perimeter_id=self.p4.id,
                                  right_read_patient_nominative=True,
                                  right_read_patient_pseudonymized=True,
                                  right_search_patients_by_ipp=True,
                                  right_search_opposed_patients=True,
                                  right_export_csv_nominative=True,
                                  right_export_csv_pseudonymized=False,
                                  right_export_jupyter_nominative=False,
                                  right_export_jupyter_pseudonymized=True)]

        target_perimeters_ids = [target_perimeters_p0, target_perimeters_p2, target_perimeters_p4_p10]
        to_find_list = [to_find_on_p0, to_find_on_p2, to_find_on_p4_p10]

        for perimeters_ids, to_find in zip(target_perimeters_ids, to_find_list):
            case = base_case.clone(params={"perimeters_ids": ",".join(map(str, perimeters_ids))},
                                   to_find=to_find)
            resp_data = self.check_list_case(case=case,
                                             other_view=AccessViewTests.get_my_data_reading_rights_view,
                                             yield_response_data=True)
            for resp_item in resp_data:
                for item in to_find:
                    if item.get("perimeter_id") == resp_item.get("perimeter_id"):
                        for k, v in resp_item.items():
                            self.assertEqual(item.get(k), v)
