from django.utils import timezone
from rest_framework import status

from accesses.models import Perimeter
from accesses.services.perimeters import perimeters_service
from accesses.services.shared import PerimeterReadRight
from accesses.tests.base import AccessesAppTestsBase
from accesses.views import PerimeterViewSet
from admin_cohort.tools.tests_tools import ListCase


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

            - With respect to this hierarchy, User T has 6 accesses defined on P0, P1, P8 and P10
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

        - With respect to this hierarchy, User Z has 6 accesses defined on P0, P1, P2, P5, P8 and P10
          allowing him to manage other accesses either on same level (S) or on inferior levels (I).
        """
        perimeters = [self.p0, self.p1, self.p2, self.p4, self.p10]
        roles = [self.role_data_reader_pseudo,
                 self.role_search_by_ipp_and_search_opposed,
                 self.role_data_reader_nomi_pseudo,
                 self.role_data_reader_nomi,
                 self.role_data_reader_pseudo]

        self.profile_y.accesses.all().update(end_datetime=timezone.now())
        for perimeter, role in zip(perimeters, roles):
            self.create_new_access_for_user(profile=self.profile_y, role=role, perimeter=perimeter, close_existing=False)

        target_perimeters = [self.aphp, self.p0, self.p4, self.p8, self.p10]

        data_read_rights_aphp = PerimeterReadRight(perimeter=self.aphp,
                                                   right_read_patient_nominative=False,
                                                   right_read_patient_pseudonymized=False,
                                                   right_search_patients_by_ipp=True,       # todo: this should be False since no read data rights
                                                   right_read_opposed_patients_data=True)   # todo: same

        data_read_rights_p0 = PerimeterReadRight(perimeter=self.p0,
                                                 right_read_patient_nominative=False,
                                                 right_read_patient_pseudonymized=True,
                                                 right_search_patients_by_ipp=True,
                                                 right_read_opposed_patients_data=True)

        data_read_rights_p4 = PerimeterReadRight(perimeter=self.p4,
                                                 right_read_patient_nominative=True,
                                                 right_read_patient_pseudonymized=True,
                                                 right_search_patients_by_ipp=True,
                                                 right_read_opposed_patients_data=True)

        data_read_rights_p8 = PerimeterReadRight(perimeter=self.p8,
                                                 right_read_patient_nominative=True,
                                                 right_read_patient_pseudonymized=True,
                                                 right_search_patients_by_ipp=True,
                                                 right_read_opposed_patients_data=True)

        data_read_rights_p10 = PerimeterReadRight(perimeter=self.p10,
                                                  right_read_patient_nominative=True,
                                                  right_read_patient_pseudonymized=True,
                                                  right_search_patients_by_ipp=True,
                                                  right_read_opposed_patients_data=True)

        expected_data_read_rights = [data_read_rights_aphp,
                                     data_read_rights_p0,
                                     data_read_rights_p4,
                                     data_read_rights_p8,
                                     data_read_rights_p10]

        data_read_rights = perimeters_service.get_data_reading_rights_on_perimeters(user=self.user_y,
                                                                                    target_perimeters=target_perimeters)
        self.assertEqual(expected_data_read_rights, data_read_rights)

