from django.utils import timezone
from rest_framework import status

from accesses.models import Perimeter
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

        target_local_ids = [self.aphp.local_id,
                            self.p0.local_id,
                            self.p4.local_id,
                            self.p8.local_id,
                            self.p10.local_id
                            ]
        data_read_rights_aphp = dict(perimeter=self.aphp,
                                     right_read_patient_nominative=False,
                                     right_read_patient_pseudonymized=False,
                                     right_search_patients_by_ipp=True,          # todo: this should be False since no read data right are given
                                     right_read_opposed_patients_data=True,      # todo: same
                                     read_role="NO READ PATIENT RIGHT")

        data_read_rights_p0 = dict(perimeter=self.p0,
                                   right_read_patient_nominative=False,
                                   right_read_patient_pseudonymized=True,
                                   right_search_patients_by_ipp=True,
                                   right_read_opposed_patients_data=True,
                                   read_role="READ_PATIENT_PSEUDO_ANONYMIZE")
        data_read_rights_p4 = dict(perimeter=self.p4,
                                   right_read_patient_nominative=True,
                                   right_read_patient_pseudonymized=True,
                                   right_search_patients_by_ipp=True,
                                   right_read_opposed_patients_data=True,
                                   read_role="READ_PATIENT_NOMINATIVE")
        data_read_rights_p8 = dict(perimeter=self.p8,
                                   right_read_patient_nominative=True,
                                   right_read_patient_pseudonymized=True,
                                   right_search_patients_by_ipp=True,
                                   right_read_opposed_patients_data=True,
                                   read_role="READ_PATIENT_NOMINATIVE")
        data_read_rights_p10 = dict(perimeter=self.p10,
                                    right_read_patient_nominative=True,
                                    right_read_patient_pseudonymized=True,
                                    right_search_patients_by_ipp=True,
                                    right_read_opposed_patients_data=True,
                                    read_role="READ_PATIENT_NOMINATIVE")

        data_read_rights = [data_read_rights_aphp,
                            data_read_rights_p0,
                            data_read_rights_p4,
                            data_read_rights_p8,
                            data_read_rights_p10]

        case = ListCase(params={"local_id": ",".join(target_local_ids)},
                        to_find=data_read_rights,
                        user=self.user_y,
                        status=status.HTTP_200_OK,
                        success=True)
        response_data = self.check_list_case(case=case,
                                             other_view=PerimeterViewTests.get_data_read_rights_on_perimeters_view,
                                             yield_response_data=True)
        for e in response_data:
            for i in case.to_find:
                if e.get("perimeter").get("id") == i.get("perimeter").id:
                    for k, v in e.items():
                        if k != "perimeter":
                            self.assertEqual(v, i.get(k))
