from typing import Union

from django.test import TestCase
from django.views import View
from rest_framework.test import APIRequestFactory, force_authenticate

from accesses.models import Role, Perimeter, Access
from admin_cohort.tests.tests_tools import new_user_and_profile
from cohort.models import Request, RequestQuerySnapshot, Folder
from exports.apps import ExportsConfig
from exports.models import InfrastructureProvider


class ExportsTestBase(TestCase):
    view_set: Union[View, None] = None
    view_root = ""
    model = None
    lookup_field = "uuid"

    def setUp(self):
        self.factory = APIRequestFactory()
        if self.view_set:
            self.list_view = self.view_set.as_view({'get': 'list'})
            self.retrieve_view = self.view_set.as_view({'get': 'retrieve'})
            self.create_view = self.view_set.as_view({'post': 'create'})
            self.patch_view = self.view_set.as_view({'patch': 'partial_update'})
            self.delete_view = self.view_set.as_view({'delete': 'destroy'})
        self.viewname_list = f"{self.view_root}-list"
        self.viewname_detail = f"{self.view_root}-detail"

        self.perimeter_aphp = Perimeter.objects.create(name="APHP", local_id="1", cohort_id="1")

        self.csv_exporter_role = Role.objects.create(name="CSV EXPORTER", right_export_csv_nominative=True)
        self.datalab_reader_role = Role.objects.create(name="DATALABS READER", right_read_datalabs=True)
        self.datalab_manager_role = Role.objects.create(name="DATALABS MANAGER", right_read_datalabs=True, right_manage_datalabs=True)

        self.datalabs_reader_user, self.datalabs_reader_profile = new_user_and_profile()
        self.datalabs_manager_user, self.datalabs_manager_profile = new_user_and_profile()
        self.exporter_user, self.exporter_profile = new_user_and_profile()
        self.user_without_rights, _ = new_user_and_profile()

        self.datalabs_reader_access = Access.objects.create(profile=self.datalabs_reader_profile,
                                                            perimeter=self.perimeter_aphp,
                                                            role=self.datalab_reader_role)
        self.datalabs_manager_access = Access.objects.create(profile=self.datalabs_manager_profile,
                                                             perimeter=self.perimeter_aphp,
                                                             role=self.datalab_manager_role)
        self.csv_exporter_access = Access.objects.create(profile=self.exporter_profile,
                                                         perimeter=self.perimeter_aphp,
                                                         role=self.csv_exporter_role)
        self.infra_provider_aphp = InfrastructureProvider.objects.create(name="APHP")
        self.folder = Folder.objects.create(name="TestFolder", owner=self.exporter_user)
        self.request = Request.objects.create(name="TestRequest", owner=self.exporter_user, parent_folder=self.folder)
        self.rqs = RequestQuerySnapshot.objects.create(owner=self.exporter_user,
                                                       request=self.request,
                                                       serialized_query="{}",
                                                       perimeters_ids=[self.perimeter_aphp.cohort_id])
        self.export_type = ExportsConfig.ExportTypes.default()

    def make_request(self, url, http_verb, request_user, request_data=None):
        handler = getattr(self.factory, http_verb)
        request = handler(path=url, data=request_data, format='json')
        force_authenticate(request, request_user)
        return request

    def check_test_list_view(self, request_user, list_url: str, expected_resp_status, result_count: int):
        request = self.make_request(url=list_url, http_verb="get", request_user=request_user)
        response = self.list_view(request)
        self.assertEqual(response.status_code, expected_resp_status)
        self.assertEqual(len(response.data), result_count)

    def check_test_retrieve_view(self, request_user, retrieve_url: str, obj_id, expected_resp_status, to_read_from_response, to_check_against):
        request = self.make_request(url=retrieve_url, http_verb="get", request_user=request_user)
        response = self.retrieve_view(request, **{self.__class__.lookup_field: obj_id})
        self.assertEqual(response.status_code, expected_resp_status)
        self.assertEqual(response.data[to_read_from_response], to_check_against)

    def check_test_create_view(self, request_user, create_url: str, request_data, expected_resp_status):
        request = self.make_request(url=create_url, http_verb="post", request_user=request_user, request_data=request_data)
        response = self.create_view(request)
        self.assertEqual(response.status_code, expected_resp_status)

    def check_test_patch_view(self, request_user, patch_url: str, request_data, obj_id, expected_resp_status, to_read_from_response,
                              to_check_against):
        request = self.make_request(url=patch_url, http_verb="patch", request_user=request_user, request_data=request_data)
        response = self.patch_view(request, **{self.lookup_field: obj_id})
        self.assertEqual(response.status_code, expected_resp_status)
        self.assertEqual(response.data[to_read_from_response], to_check_against)

    def check_test_delete_view(self, request_user, delete_url: str, obj_id, expected_resp_status):
        request = self.make_request(url=delete_url, http_verb="delete", request_user=request_user)
        response = self.delete_view(request, **{self.lookup_field: obj_id})
        self.assertEqual(response.status_code, expected_resp_status)
