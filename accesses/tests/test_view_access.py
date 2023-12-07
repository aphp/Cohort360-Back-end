from datetime import timedelta

from django.db.models import Q
from django.utils import timezone
from rest_framework import status

from accesses.models import Access, Role
from accesses.tests.base import AccessesAppTestsBase, ALL_FALSY_RIGHTS
from accesses.views import AccessViewSet
from admin_cohort.tools.tests_tools import CaseRetrieveFilter, CreateCase, new_user_and_profile, PatchCase


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
        self.user_data_accesses_manager_on_aphp, _profile = new_user_and_profile(email="user_data_accesses_manager@aphp.fr")
        Access.objects.create(profile=_profile, role=self.role_data_accesses_manager, perimeter=self.aphp)

        _, profile = new_user_and_profile(email="user_01@aphp.fr")
        basic_role = Role.objects.create(**{**ALL_FALSY_RIGHTS,
                                            "name": "DATA NOMI READER",
                                            "right_read_patient_nominative": True})
        self.basic_access_data = {"profile_id": profile.id,
                                  "role_id": basic_role.id,
                                  "perimeter_id": self.aphp.id
                                  }
        self.basic_retrieve_filter = AccessesRetrieveFilter(**self.basic_access_data)

    def check_close_case(self, close_case: PatchCase):
        self.check_patch_case(close_case, other_view=AccessViewTests.close_view)
        access = Access.objects.get(Q(**close_case.initial_data))
        self.assertTrue(access.end_datetime < timezone.now())
        self.assertFalse(access.is_valid)

    def test_successfully_create_access(self):
        case = CreateCase(data=self.basic_access_data,
                          user=self.user_data_accesses_manager_on_aphp,
                          status=status.HTTP_201_CREATED,
                          success=True,
                          retrieve_filter=self.basic_retrieve_filter)
        self.check_create_case(case)

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
        user_non_accesses_manager, profile = new_user_and_profile(email="user_non_accesses_manager@aphp.fr")
        Access.objects.create(profile=profile, role=self.role_nomi_reader_nomi_csv_exporter, perimeter=self.aphp)
        self.check_create_case(CreateCase(data=self.basic_access_data,
                                          user=user_non_accesses_manager,
                                          status=status.HTTP_403_FORBIDDEN,
                                          success=False,
                                          retrieve_filter=self.basic_retrieve_filter))

    def test_successfully_close_access(self):
        start_datetime = timezone.now()
        case = PatchCase(initial_data={**self.basic_access_data, "start_datetime": start_datetime},
                         data_to_update={},
                         user=self.user_data_accesses_manager_on_aphp,
                         status=status.HTTP_200_OK,
                         success=True)
        self.check_close_case(case)

    def test_error_close_a_future_access(self):
        start_datetime = timezone.now() + timedelta(weeks=1)
        case = PatchCase(initial_data={**self.basic_access_data, "start_datetime": start_datetime},
                         data_to_update={},
                         user=self.user_data_accesses_manager_on_aphp,
                         status=status.HTTP_403_FORBIDDEN,
                         success=False)
        self.check_close_case(case)

    def test_error_close_an_already_closed_access(self):
        start_datetime = timezone.now() + timedelta(weeks=1)
        case = PatchCase(initial_data={**self.basic_access_data, "start_datetime": start_datetime},
                         data_to_update={},
                         user=self.user_data_accesses_manager_on_aphp,
                         status=status.HTTP_403_FORBIDDEN,
                         success=False)
        self.check_close_case(case)

    def test_error_patch_access_as_non_accesses_manager(self):
        ...

    def test_list_accesses_of_user_x_for_user_y(self):
        ...

    def test_list_accesses_on_perimeter_Px_for_user_y(self):
        ...
