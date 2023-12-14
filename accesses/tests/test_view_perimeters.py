from django.utils import timezone
from rest_framework import status

from accesses.models import Perimeter
from accesses.services.shared import PerimeterReadRight
from accesses.tests.base import AccessesAppTestsBase
from accesses.views import PerimeterViewSet
from admin_cohort.tools.tests_tools import ListCase, new_user_and_profile


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
            data_read_rights_p1 = PerimeterReadRight(perimeter=self.p1,
                                                     right_read_patient_nominative=False,
                                                     right_read_patient_pseudonymized=False,
                                                     right_search_patients_by_ipp=True,
                                                     right_read_opposed_patients_data=True)

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

            expected_data_read_rights = [data_read_rights_p1,
                                         data_read_rights_p5,
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

    def test_check_read_patient_data_rights(self):
        """                                                    APHP
                                     ___________________________|____________________________
                                    |                           |                           |
                                   P0                          P1                          P2
                          _________|__________           ______|_______           _________|__________
                         |         |         |          |             |          |         |         |
                         P3        P4        P5         P6            P7         P8        P9       P10
                             ______|_______                                                    ______|_______
                            |             |                                                   |             |
                           P11           P12                                                 P13           P14

        """
        base_case = ListCase(params={},
                             to_find=[],
                             user=None,
                             status=status.HTTP_200_OK,
                             success=True)

        def check_read_patient_data_rights_nomi():
            perimeters = [self.aphp, self.p1, self.p4, self.p10]
            roles = [self.role_data_reader_pseudo,
                     self.role_search_by_ipp_and_search_opposed,
                     self.role_data_reader_nomi_pseudo,
                     self.role_data_reader_nomi]

            self.profile_z.accesses.all().update(end_datetime=timezone.now())
            for perimeter, role in zip(perimeters, roles):
                self.create_new_access_for_user(profile=self.profile_z, role=role, perimeter=perimeter, close_existing=False)
            return base_case.clone(user=self.user_z,
                                   params={"mode": "max"},
                                   to_find={"allow_read_patient_data_nomi": True,
                                            "allow_lookup_opposed_patients": True})

        def check_read_patient_data_rights_pseudo():
            perimeters = [self.p1, self.p4]
            roles = [self.role_data_reader_pseudo,
                     self.role_search_by_ipp_and_search_opposed]

            self.profile_t.accesses.all().update(end_datetime=timezone.now())
            for perimeter, role in zip(perimeters, roles):
                self.create_new_access_for_user(profile=self.profile_t, role=role, perimeter=perimeter, close_existing=False)
            return base_case.clone(user=self.user_t,
                                   params={"mode": "min"},
                                   to_find={"allow_read_patient_data_nomi": False,
                                            "allow_lookup_opposed_patients": True})

        def check_read_patient_data_rights_with_user_having_no_data_rights():
            perimeters = [self.aphp, self.p2]
            roles = [self.role_data_accesses_manager,
                     self.role_export_accesses_manager]

            self.profile_y.accesses.all().update(end_datetime=timezone.now())
            for perimeter, role in zip(perimeters, roles):
                self.create_new_access_for_user(profile=self.profile_y, role=role, perimeter=perimeter, close_existing=False)
            return base_case.clone(title="user without rights",
                                   user=self.user_y,
                                   params={"mode": "min"},
                                   status=status.HTTP_404_NOT_FOUND,
                                   success=False)

        def check_read_patient_data_rights_without_read_mode():
            self.user_w, self.profile_w = new_user_and_profile(email="user_w@aphp.fr")
            self.create_new_access_for_user(profile=self.profile_w, role=self.role_data_reader_nomi, perimeter=self.aphp)
            return base_case.clone(title="missing mode param",
                                   user=self.user_w,
                                   params={},
                                   status=status.HTTP_400_BAD_REQUEST,
                                   success=False)

        def check_read_patient_data_rights_with_wrong_read_mode():
            self.user_u, self.profile_u = new_user_and_profile(email="user_u@aphp.fr")
            self.create_new_access_for_user(profile=self.profile_u, role=self.role_data_reader_nomi, perimeter=self.aphp)
            return base_case.clone(title="wrong value for mode param",
                                   user=self.user_u,
                                   params={"mode": "wrong_value"},
                                   status=status.HTTP_400_BAD_REQUEST,
                                   success=False)

        case_1 = check_read_patient_data_rights_nomi()
        case_2 = check_read_patient_data_rights_pseudo()
        case_3 = check_read_patient_data_rights_with_user_having_no_data_rights()
        case_4 = check_read_patient_data_rights_without_read_mode()
        case_5 = check_read_patient_data_rights_with_wrong_read_mode()

        for case in (case_1, case_2, case_3, case_4, case_5):
            response_data = self.check_list_case(case=case,
                                                 other_view=PerimeterViewTests.check_read_patient_data_rights_view,
                                                 yield_response_data=True)
            if case.success:
                self.assertEqual(response_data, case.to_find)

