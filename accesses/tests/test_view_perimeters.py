from unittest import mock
from unittest.mock import MagicMock

from django.utils import timezone
from rest_framework import status

from accesses.models import Perimeter
from accesses.services.shared import PerimeterReadRight
from accesses.tests.base import AccessesAppTestsBase
from accesses.views import PerimeterViewSet
from admin_cohort.tests.tests_tools import ListCase, new_user_and_profile


class PerimeterViewTests(AccessesAppTestsBase):
    objects_url = "/perimeters/"
    retrieve_view = PerimeterViewSet.as_view({'get': 'retrieve'})
    list_view = PerimeterViewSet.as_view({'get': 'list'})
    create_view = PerimeterViewSet.as_view({'post': 'create'})
    delete_view = PerimeterViewSet.as_view({'delete': 'destroy'})
    update_view = PerimeterViewSet.as_view({'patch': 'partial_update'})
    close_view = PerimeterViewSet.as_view(actions={'patch': 'close'})
    get_manageable_perimeters_view = PerimeterViewSet.as_view(actions={'get': 'get_manageable_perimeters'})
    get_data_read_rights_on_perimeters_view = PerimeterViewSet.as_view(actions={'get': 'get_data_read_rights_on_perimeters'})
    check_read_patient_data_rights_view = PerimeterViewSet.as_view(actions={'get': 'check_read_patient_data_rights'})
    model = Perimeter
    model_objects = Perimeter.objects
    model_fields = Perimeter._meta.fields

    def setUp(self):
        super().setUp()
        self.base_case = ListCase(params={},
                                  to_find=[],
                                  user=None,
                                  success=True,
                                  status=status.HTTP_200_OK)

    def test_get_manageable_perimeters(self):
        base_case = ListCase(params={},
                             to_find=[],
                             user=None,
                             status=status.HTTP_200_OK,
                             success=True)

        def get_manageable_perimeters_1():
            """                                            APHP
                                 ___________________________|____________________________
                                |                           |                           |
                               P0 (S+I)                    P1 (S+I)                    P2 (S+I)
                      _________|__________           ______|_______           _________|__________
                     |         |         |          |             |          |         |         |
                     P3        P4       P5 (S+I)   P6            P7         P8 (S+I)  P9        P10
                         ______|_______                                                    ______|_______
                        |             |                                                   |             |
                       P11           P12                                                 P13           P14

            - With respect to this hierarchy, User Z has 6 accesses defined on P0, P1, P2, P5, P8 and P10
              allowing him to manage other accesses either on same level (S) or on inferior levels (I).
            """
            perimeters = [self.p0, self.p1, self.p2, self.p5, self.p8]
            roles = [self.role_data_accesses_manager,
                     self.role_admin_accesses_reader,
                     self.role_admin_accesses_manager,
                     self.role_export_accesses_manager,
                     self.role_data_accesses_manager]

            for perimeter, role in zip(perimeters, roles):
                self.create_new_access_for_user(profile=self.profile_z, role=role, perimeter=perimeter, close_existing=False)

            top_manageable_perimeters_ids = [self.p0.id, self.p2.id]
            return base_case.clone(user=self.user_z,
                                   to_find=top_manageable_perimeters_ids)

        def get_manageable_perimeters_2():
            """                                            APHP
                                 ___________________________|____________________________
                                |                           |                           |
                               P0 (I)                      P1 (S+I)                    P2
                      _________|__________           ______|_______           _________|__________
                     |         |         |          |             |          |         |         |
                     P3        P4       P5         P6            P7         P8 (S)    P9        P10 (I)
                         ______|_______                                                    ______|_______
                        |             |                                                   |             |
                       P11           P12                                                 P13           P14

            - With respect to this hierarchy, User T has 4 accesses defined on P0, P1, P8 and P10
              allowing him to manage other accesses either on same level (S) or on inferior levels (I).
            """
            perimeters = [self.p0, self.p1, self.p8, self.p10]
            roles = [self.role_data_accesses_manager_inf_levels,
                     self.role_admin_accesses_manager,
                     self.role_admin_accesses_manager_same_level,
                     self.role_data_accesses_manager_inf_levels]

            for perimeter, role in zip(perimeters, roles):
                self.create_new_access_for_user(profile=self.profile_t, role=role, perimeter=perimeter, close_existing=False)

            top_manageable_perimeters_ids = [self.p3.id, self.p4.id, self.p5.id,
                                             self.p1.id,
                                             self.p8.id,
                                             self.p13.id, self.p14.id]
            return base_case.clone(user=self.user_t,
                                   to_find=top_manageable_perimeters_ids)

        case_1 = get_manageable_perimeters_1()
        case_2 = get_manageable_perimeters_2()

        for case in (case_1, case_2):
            response_data = self.check_list_case(case=case,
                                                 other_view=PerimeterViewTests.get_manageable_perimeters_view,
                                                 yield_response_data=True)
            perimeter_ids_in_response = [e.get("id") for e in response_data]
            self.assertEqual(sorted(perimeter_ids_in_response),
                             sorted(case.to_find))

    def test_get_data_read_rights_on_perimeters(self):
        """                                            APHP
                             ___________________________|____________________________
                            |                           |                           |
                          -P0-                        -P1-                        -P2-
                  _________|__________           ______|_______           _________|__________
                 |         |         |          |             |          |         |         |
                 P3       -P4-       P5         P6            P7         P8        P9       -P10-
                     ______|_______                                                    ______|_______
                    |             |                                                   |             |
                   P11           P12                                                 P13           P14

        """
        base_case = ListCase(params={},
                             to_find=[],
                             user=self.user_y,
                             status=status.HTTP_200_OK,
                             success=True)

        perimeters = [self.p0, self.p1, self.p2, self.p4, self.p10]
        roles = [self.role_data_reader_pseudo,
                 self.role_search_by_ipp_and_search_opposed,
                 self.role_data_reader_nomi_pseudo,
                 self.role_data_reader_nomi,
                 self.role_data_reader_pseudo]

        self.profile_y.accesses.all().update(end_datetime=timezone.now())
        for perimeter, role in zip(perimeters, roles):
            self.create_new_access_for_user(profile=self.profile_y, role=role, perimeter=perimeter, close_existing=False)

        def get_data_read_rights_on_perimeters_1():
            data_read_rights_p0 = PerimeterReadRight(perimeter=self.p0,
                                                     right_read_patient_nominative=False,
                                                     right_read_patient_pseudonymized=True,
                                                     right_search_patients_by_ipp=True,
                                                     right_read_opposed_patients_data=True)

            data_read_rights_p2 = PerimeterReadRight(perimeter=self.p2,
                                                     right_read_patient_nominative=True,
                                                     right_read_patient_pseudonymized=True,
                                                     right_search_patients_by_ipp=True,
                                                     right_read_opposed_patients_data=True)

            data_read_rights_p4 = PerimeterReadRight(perimeter=self.p4,
                                                     right_read_patient_nominative=True,
                                                     right_read_patient_pseudonymized=True,
                                                     right_search_patients_by_ipp=True,
                                                     right_read_opposed_patients_data=True)

            expected_data_read_rights = [data_read_rights_p0,
                                         data_read_rights_p2,
                                         data_read_rights_p4]
            return base_case.clone(params={},
                                   to_find=expected_data_read_rights)

        def get_data_read_rights_on_perimeters_2():
            data_read_rights_p5 = PerimeterReadRight(perimeter=self.p5,
                                                     right_read_patient_nominative=False,
                                                     right_read_patient_pseudonymized=True,
                                                     right_search_patients_by_ipp=True,
                                                     right_read_opposed_patients_data=True)

            data_read_rights_p9 = PerimeterReadRight(perimeter=self.p9,
                                                     right_read_patient_nominative=True,
                                                     right_read_patient_pseudonymized=True,
                                                     right_search_patients_by_ipp=True,
                                                     right_read_opposed_patients_data=True)

            expected_data_read_rights = [data_read_rights_p5,
                                         data_read_rights_p9]

            target_local_ids = [self.p1.local_id,
                                self.p5.local_id,
                                self.p9.local_id]

            return base_case.clone(params={"local_id": ",".join(target_local_ids)},
                                   to_find=expected_data_read_rights)

        case_1 = get_data_read_rights_on_perimeters_1()
        case_2 = get_data_read_rights_on_perimeters_2()

        for case in (case_1, case_2):
            response_results = self.check_get_paged_list_case(case=case,
                                                              other_view=PerimeterViewTests.get_data_read_rights_on_perimeters_view,
                                                              check_found_objects=False,
                                                              yield_response_results=True)
            for result_item in response_results:
                for expected_dr in case.to_find:
                    if expected_dr.perimeter.id == result_item.get("perimeter").get("id"):
                        for k, v in result_item.items():
                            if k != "perimeter":
                                self.assertEqual(getattr(expected_dr, k, False), v)

    @mock.patch('accesses.views.perimeter.perimeters_service.get_target_perimeters')
    def check_list_case_with_mock(self, case: ListCase, mock_get_target_perimeters: MagicMock, check_mock_was_called=True):
        mock_get_target_perimeters.return_value = Perimeter.objects.filter(cohort_id__in=case.params.get("cohort_ids", "").split(","))
        response_data = self.check_list_case(case=case,
                                             other_view=PerimeterViewTests.check_read_patient_data_rights_view,
                                             yield_response_data=True)
        if check_mock_was_called:
            mock_get_target_perimeters.assert_called()
        if case.success:
            self.assertEqual(response_data, case.to_find)

    def make_accesses_for_user(self, profile, perimeters, roles):
        profile.accesses.all().update(end_datetime=timezone.now())
        for perimeter, role in zip(perimeters, roles):
            self.create_new_access_for_user(profile=profile, role=role, perimeter=perimeter, close_existing=False)

#                                                       APHP
#                             ___________________________|____________________________
#                            |                           |                           |
#                            P0                          P1                          P2
#                   _________|__________           ______|_______           _________|__________
#                  |         |         |          |             |          |         |         |
#                  P3        P4        P5         P6            P7         P8        P9       P10
#                      ______|_______                                                    ______|_______
#                     |             |                                                   |             |
#                    P11           P12                                                 P13           P14
#
    def test_read_patient_data_rights_case_1(self):
        perimeters = [self.aphp, self.p1]
        roles = [self.role_data_reader_pseudo,
                 self.role_data_reader_nomi]
        self.make_accesses_for_user(self.profile_z, perimeters, roles)

        cohort_ids = ",".join([self.p1.cohort_id])
        case = self.base_case.clone(user=self.user_z,
                                    params={"cohort_ids": cohort_ids, "mode": "min"},
                                    to_find={"allow_read_patient_data_nomi": True,
                                             "allow_lookup_opposed_patients": False,
                                             "allow_read_patient_without_perimeter_limit": False
                                             })
        self.check_list_case_with_mock(case)

    def test_read_patient_data_rights_case_2(self):
        perimeters = [self.p1, self.aphp]
        roles = [self.role_data_reader_pseudo,
                 self.role_data_reader_nomi]
        self.make_accesses_for_user(self.profile_z, perimeters, roles)

        cohort_ids = ",".join([self.p1.cohort_id, self.p5.cohort_id])
        case = self.base_case.clone(user=self.user_z,
                                    params={"cohort_ids": cohort_ids, "mode": "min"},
                                    to_find={"allow_read_patient_data_nomi": True,
                                             "allow_lookup_opposed_patients": False,
                                             "allow_read_patient_without_perimeter_limit": False})
        self.check_list_case_with_mock(case)

    def test_read_patient_data_rights_case_3(self):
        perimeters = [self.aphp, self.p0, self.p10]
        roles = [self.role_data_reader_pseudo,
                 self.role_data_reader_nomi,
                 self.role_data_reader_nomi]
        self.make_accesses_for_user(self.profile_z, perimeters, roles)
        cohort_ids = ",".join([self.p5.cohort_id, self.p8.cohort_id])
        case_1 = self.base_case.clone(user=self.user_z,
                                      params={"cohort_ids": cohort_ids, "mode": "max"},
                                      to_find={"allow_read_patient_data_nomi": True,
                                               "allow_lookup_opposed_patients": False,
                                               "allow_read_patient_without_perimeter_limit": False})
        case_2 = case_1.clone(params={"cohort_ids": cohort_ids, "mode": "min"},
                              to_find={"allow_read_patient_data_nomi": False,
                                       "allow_lookup_opposed_patients": False,
                                       "allow_read_patient_without_perimeter_limit": False})
        self.check_list_case_with_mock(case_1)
        self.check_list_case_with_mock(case_2)

    def test_read_patient_data_rights_case_4(self):
        perimeters = [self.aphp, self.p1, self.p4, self.p10]
        roles = [self.role_data_reader_pseudo,
                 self.role_search_by_ipp_and_search_opposed,
                 self.role_data_reader_nomi_pseudo,
                 self.role_data_reader_nomi]
        self.make_accesses_for_user(self.profile_z, perimeters, roles)

        cohort_ids = ",".join([self.aphp.cohort_id, self.p1.cohort_id, self.p4.cohort_id, self.p10.cohort_id])
        case_1 = self.base_case.clone(user=self.user_z,
                                      params={"cohort_ids": cohort_ids, "mode": "min"},
                                      to_find={"allow_read_patient_data_nomi": False,
                                               "allow_lookup_opposed_patients": True,
                                               "allow_read_patient_without_perimeter_limit": False})
        case_2 = case_1.clone(params={"cohort_ids": cohort_ids, "mode": "max"},
                              to_find={"allow_read_patient_data_nomi": True,
                                       "allow_lookup_opposed_patients": True,
                                       "allow_read_patient_without_perimeter_limit": False})
        self.check_list_case_with_mock(case_1)
        self.check_list_case_with_mock(case_2)

    def test_read_patient_data_rights_case_5(self):
        perimeters = [self.p2, self.p3]
        roles = [self.role_data_reader_pseudo,
                 self.role_data_reader_pseudo]
        self.make_accesses_for_user(self.profile_z, perimeters, roles)

        cohort_ids = ",".join([self.p2.cohort_id, self.p9.cohort_id])
        case_1 = self.base_case.clone(user=self.user_z,
                                      params={"cohort_ids": cohort_ids, "mode": "max"},
                                      to_find={"allow_read_patient_data_nomi": False,
                                               "allow_lookup_opposed_patients": False,
                                               "allow_read_patient_without_perimeter_limit": False})
        case_2 = case_1.clone(params={"cohort_ids": cohort_ids, "mode": "min"},
                              to_find={"allow_read_patient_data_nomi": False,
                                       "allow_lookup_opposed_patients": False,
                                       "allow_read_patient_without_perimeter_limit": False})
        self.check_list_case_with_mock(case_1)
        self.check_list_case_with_mock(case_2)

    def test_read_patient_data_rights_case_6(self):
        perimeters = [self.p1, self.p4]
        roles = [self.role_data_reader_pseudo,
                 self.role_data_reader_nomi]
        self.make_accesses_for_user(self.profile_t, perimeters, roles)

        cohort_ids = ",".join([self.p6.cohort_id, self.p12.cohort_id])
        case = self.base_case.clone(user=self.user_t,
                                    params={"cohort_ids": cohort_ids, "mode": "min"},
                                    to_find={"allow_read_patient_data_nomi": False,
                                             "allow_lookup_opposed_patients": False,
                                             "allow_read_patient_without_perimeter_limit": False})
        self.check_list_case_with_mock(case)

    def test_read_patient_data_rights_case_7(self):
        perimeters = [self.p1, self.p4]
        roles = [self.role_data_reader_full_access]
        self.make_accesses_for_user(self.profile_t, perimeters, roles)

        cohort_ids = ",".join([self.p6.cohort_id, self.p12.cohort_id])
        case = self.base_case.clone(user=self.user_t,
                                    params={"cohort_ids": cohort_ids, "mode": "min"},
                                    to_find={"allow_read_patient_data_nomi": True,
                                             "allow_lookup_opposed_patients": True,
                                             "allow_read_patient_without_perimeter_limit": True})
        self.check_list_case_with_mock(case, check_mock_was_called=False)

    def test_read_patient_data_rights_case_8(self):
        perimeters = [self.p1, self.p4]
        roles = [self.role_data_reader_full_access]
        self.make_accesses_for_user(self.profile_t, perimeters, roles)

        cohort_ids = ",".join([self.p6.cohort_id, self.p12.cohort_id])
        case = self.base_case.clone(user=self.user_t,
                                    params={"cohort_ids": cohort_ids, "mode": "max"},
                                    to_find={"allow_read_patient_data_nomi": True,
                                             "allow_lookup_opposed_patients": True,
                                             "allow_read_patient_without_perimeter_limit": True})
        self.check_list_case_with_mock(case, check_mock_was_called=False)

    def test_read_patient_data_rights_missing_access_on_some_target_perimeters(self):
        perimeters = [self.p1, self.p2]
        roles = [self.role_data_reader_pseudo,
                 self.role_search_by_ipp_and_search_opposed]
        self.make_accesses_for_user(self.profile_t, perimeters, roles)

        cohort_ids = ",".join([self.p1.cohort_id, self.p5.cohort_id])
        case_with_mode_min = self.base_case.clone(user=self.user_t,
                                                  params={"cohort_ids": cohort_ids, "mode": "min"},
                                                  success=False,
                                                  status=status.HTTP_404_NOT_FOUND)
        case_with_mode_max = self.base_case.clone(user=self.user_t,
                                                  params={"cohort_ids": cohort_ids, "mode": "max"},
                                                  to_find={"allow_read_patient_data_nomi": False,
                                                           "allow_lookup_opposed_patients": True,
                                                           "allow_read_patient_without_perimeter_limit": False})
        for case in (case_with_mode_min, case_with_mode_max):
            self.check_list_case_with_mock(case)

    def test_read_patient_data_rights_with_user_having_no_data_rights(self):
        perimeters = [self.aphp, self.p2]
        roles = [self.role_data_accesses_manager,
                 self.role_export_accesses_manager]
        self.make_accesses_for_user(self.profile_y, perimeters, roles)

        cohort_ids = ",".join([self.aphp.cohort_id, self.p2.cohort_id])
        case = self.base_case.clone(title="user without rights",
                                    user=self.user_y,
                                    params={"cohort_ids": cohort_ids, "mode": "min"},
                                    status=status.HTTP_404_NOT_FOUND,
                                    success=False)
        self.check_list_case_with_mock(case)

    def test_read_patient_data_rights_without_read_mode(self):
        self.user_w, self.profile_w = new_user_and_profile()
        self.create_new_access_for_user(profile=self.profile_w, role=self.role_data_reader_nomi, perimeter=self.aphp)
        case = self.base_case.clone(title="missing mode param",
                                    user=self.user_w,
                                    params={},
                                    status=status.HTTP_400_BAD_REQUEST,
                                    success=False)
        self.check_list_case_with_mock(case, check_mock_was_called=False)

    def test_read_patient_data_rights_with_wrong_read_mode(self):
        self.user_u, self.profile_u = new_user_and_profile()
        self.create_new_access_for_user(profile=self.profile_u, role=self.role_data_reader_nomi, perimeter=self.aphp)
        case = self.base_case.clone(title="wrong value for mode param",
                                    user=self.user_u,
                                    params={"cohort_ids": "", "mode": "wrong_value"},
                                    status=status.HTTP_400_BAD_REQUEST,
                                    success=False)
        self.check_list_case_with_mock(case, check_mock_was_called=False)
