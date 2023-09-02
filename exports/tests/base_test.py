from typing import Union

from django.test import TestCase
from django.views import View
from rest_framework.test import APIRequestFactory, force_authenticate

from accesses.models import Role, Perimeter, Access
from admin_cohort.tools.tests_tools import new_user_and_profile


class ExportsTestBase(TestCase):
    view_set: Union[View, None] = None
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

        self.workspaces_reader_user, self.profile1 = new_user_and_profile(firstname="Workspaces",
                                                                          lastname="READER",
                                                                          email=f"w.r@aphp.fr")
        self.workspaces_reader_access = Access.objects.create(profile=self.profile1,
                                                              perimeter=Perimeter.objects.create(name="Perim1", local_id="1"),
                                                              role=Role.objects.create(name="WORKSPACES READER",
                                                                                       right_read_env_unix_users=True))
        self.workspaces_manager_user, self.profile2 = new_user_and_profile(firstname="Workspaces",
                                                                           lastname="MANAGER",
                                                                           email=f"w.m@aphp.fr")
        self.workspaces_manager_access = Access.objects.create(profile=self.profile2,
                                                               perimeter=Perimeter.objects.create(name="Perim2", local_id="2"),
                                                               role=Role.objects.create(name="WORKSPACES MANAGER",
                                                                                        right_read_env_unix_users=True,
                                                                                        right_manage_env_unix_users=True))

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
