from django.urls import reverse
from rest_framework import status

from exports.models import Datalab, InfrastructureProvider
from exports.tests.base_test import ExportsTestBase
from exports.views import DatalabViewSet


class DatalabViewSetTest(ExportsTestBase):
    view_set = DatalabViewSet
    view_root = "exports:datalabs"
    model = Datalab

    def setUp(self):
        super().setUp()
        self.datalabs = [Datalab.objects.create(name=f"datalab_{i}",
                                                infrastructure_provider=self.infra_provider_aphp) for i in range(5)]
        self.target_datalab_to_retrieve = self.datalabs[0]
        self.target_datalab_to_patch = self.datalabs[1]
        self.target_datalab_to_delete = self.datalabs[2]

    def test_list_datalabs(self):
        list_url = reverse(viewname=self.viewname_list)
        self.check_test_list_view(list_url=list_url,
                                  request_user=self.datalabs_reader_user,
                                  expected_resp_status=status.HTTP_200_OK,
                                  result_count=len(self.datalabs)-1)

    def test_retrieve_datalab(self):
        retrieve_url = reverse(viewname=self.viewname_detail, args=[self.target_datalab_to_retrieve.uuid])
        check_against = {'uuid': self.infra_provider_aphp.uuid, 'name': self.infra_provider_aphp.name}
        self.check_test_retrieve_view(request_user=self.datalabs_reader_user,
                                      retrieve_url=retrieve_url,
                                      obj_id=self.target_datalab_to_retrieve.uuid,
                                      expected_resp_status=status.HTTP_200_OK,
                                      to_read_from_response='infrastructure_provider',
                                      to_check_against=check_against)

    def test_create_datalab(self):
        create_url = reverse(viewname=self.viewname_list)
        self.check_test_create_view(request_user=self.datalabs_manager_user,
                                    create_url=create_url,
                                    request_data={"name": "main_datalab", "infrastructure_provider": self.infra_provider_aphp.uuid},
                                    expected_resp_status=status.HTTP_201_CREATED)

    def test_error_create_datalab_with_no_right(self):
        create_url = reverse(viewname=self.viewname_list)
        self.check_test_create_view(request_user=self.user_without_rights,
                                    create_url=create_url,
                                    request_data={"infrastructure_provider": self.infra_provider_aphp.uuid},
                                    expected_resp_status=status.HTTP_403_FORBIDDEN)

    def test_patch_datalab(self):
        infra_provider_ext = InfrastructureProvider.objects.create(name="Exterior")
        patch_url = reverse(viewname=self.viewname_detail, args=[self.target_datalab_to_patch.uuid])
        patch_data = {'infrastructure_provider': infra_provider_ext.uuid}
        patch_result = {'uuid': infra_provider_ext.uuid, 'name': infra_provider_ext.name}
        self.check_test_patch_view(request_user=self.datalabs_manager_user,
                                   patch_url=patch_url,
                                   obj_id=self.target_datalab_to_patch.uuid,
                                   request_data=patch_data,
                                   expected_resp_status=status.HTTP_200_OK,
                                   to_read_from_response='infrastructure_provider',
                                   to_check_against=patch_result)
