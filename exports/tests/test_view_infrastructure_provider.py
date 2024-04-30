from django.urls import reverse
from rest_framework import status

from exports.models import InfrastructureProvider
from exports.tests.base_test import ExportsTestBase
from exports.views import InfrastructureProviderViewSet


class InfrastructureProviderViewSetTest(ExportsTestBase):
    view_set = InfrastructureProviderViewSet
    view_root = "exports:infrastructure_providers"
    model = InfrastructureProvider

    def setUp(self):
        super().setUp()
        self.infra_providers = [InfrastructureProvider.objects.create(name=f"infra_provider_{i}")
                                for i in range(5)]
        self.target_infra_provider_to_retrieve = self.infra_providers[0]
        self.target_infra_provider_to_patch = self.infra_providers[1]
        self.target_infra_provider_to_delete = self.infra_providers[2]

    def test_list_infrastructure_provider(self):
        list_url = reverse(viewname=self.viewname_list)
        self.check_test_list_view(list_url=list_url,
                                  request_user=self.datalabs_reader_user,
                                  expected_resp_status=status.HTTP_200_OK,
                                  result_count=len(self.infra_providers)-1)

    def test_retrieve_infrastructure_provider(self):
        retrieve_url = reverse(viewname=self.viewname_detail, args=[self.target_infra_provider_to_retrieve.uuid])
        self.check_test_retrieve_view(request_user=self.datalabs_reader_user,
                                      retrieve_url=retrieve_url,
                                      obj_id=self.target_infra_provider_to_retrieve.uuid,
                                      expected_resp_status=status.HTTP_200_OK,
                                      to_read_from_response='name',
                                      to_check_against=self.target_infra_provider_to_retrieve.name)

    def test_create_infrastructure_provider(self):
        create_url = reverse(viewname=self.viewname_list)
        self.check_test_create_view(request_user=self.datalabs_manager_user,
                                    create_url=create_url,
                                    request_data={"name": "brand_new_infra_provider"},
                                    expected_resp_status=status.HTTP_201_CREATED)

    def test_create_infrastructure_provider_with_no_right(self):
        create_url = reverse(viewname=self.viewname_list)
        self.check_test_create_view(request_user=self.user_without_rights,
                                    create_url=create_url,
                                    request_data={"name": "brand_new_infra_provider"},
                                    expected_resp_status=status.HTTP_403_FORBIDDEN)

    def test_patch_infrastructure_provider(self):
        patch_url = reverse(viewname=self.viewname_detail, args=[self.target_infra_provider_to_patch.uuid])
        patch_data = {'name': "infra_provider_99"}
        self.check_test_patch_view(request_user=self.datalabs_manager_user,
                                   patch_url=patch_url,
                                   obj_id=self.target_infra_provider_to_patch.uuid,
                                   request_data=patch_data,
                                   expected_resp_status=status.HTTP_200_OK,
                                   to_read_from_response='name',
                                   to_check_against=patch_data['name'])

    def test_delete_infrastructure_provider(self):
        delete_url = reverse(viewname=self.viewname_detail, args=[self.target_infra_provider_to_delete.uuid])
        self.check_test_delete_view(request_user=self.datalabs_manager_user,
                                    delete_url=delete_url,
                                    obj_id=self.target_infra_provider_to_delete.uuid,
                                    expected_resp_status=status.HTTP_204_NO_CONTENT)
