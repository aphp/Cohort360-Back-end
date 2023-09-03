from django.urls import reverse
from rest_framework import status

from exports.models import Export, Datalab
from exports.tests.base_test import ExportsTestBase
from exports.types import ExportType, ExportStatus
from exports.views import ExportViewSet


class ExportViewSetTestBase(ExportsTestBase):
    view_set = ExportViewSet
    view_root = "exports:v1:exports"
    model = Export

    def setUp(self):
        super().setUp()
        self.datalab = Datalab.objects.create(infrastructure_provider=self.infra_provider_aphp)
        self.exports = [Export.objects.create(name=f"Export_{i}",
                                              output_format=ExportType.CSV,
                                              owner=self.workspaces_manager_user,
                                              datalab=self.datalab,
                                              status=ExportStatus.PENDING,
                                              target_name="12345_09092023_151500") for i in range(5)]
        self.target_export_to_retrieve = self.exports[0]
        self.target_export_to_patch = self.exports[1]
        self.target_export_to_delete = self.exports[2]

    def test_list_exports(self):
        list_url = reverse(viewname=self.viewname_list)
        self.check_test_list_view(list_url=list_url,
                                  request_user=self.workspaces_reader_user,
                                  expected_resp_status=status.HTTP_200_OK,
                                  result_count=len(self.exports)-1)

    def test_retrieve_export(self):
        retrieve_url = reverse(viewname=self.viewname_detail, args=[self.target_export_to_retrieve.uuid])
        self.check_test_retrieve_view(request_user=self.workspaces_reader_user,
                                      retrieve_url=retrieve_url,
                                      obj_id=self.target_export_to_retrieve.uuid,
                                      expected_resp_status=status.HTTP_200_OK,
                                      to_read_from_response='name',
                                      to_check_against=self.target_export_to_retrieve.name)

    def test_create_export(self):
        create_url = reverse(viewname=self.viewname_list)
        request_data = {"name": "Special Export",
                        "output_format": ExportType.CSV,
                        "owner": self.workspaces_manager_user.pk,
                        "datalab": self.datalab.uuid,
                        "status": ExportStatus.PENDING,
                        "target_name": "12345_09092023_151500",
                        "export_tables": [dict(name=f"Some export table")]
                        }
        self.check_test_create_view(request_user=self.workspaces_manager_user,
                                    create_url=create_url,
                                    request_data=request_data,
                                    expected_resp_status=status.HTTP_201_CREATED)

    def test_patch_export(self):
        patch_url = reverse(viewname=self.viewname_detail, args=[self.target_export_to_patch.uuid])
        patch_data = {'status': ExportStatus.DELIVERED}
        self.check_test_patch_view(request_user=self.workspaces_manager_user,
                                   patch_url=patch_url,
                                   obj_id=self.target_export_to_patch.uuid,
                                   request_data=patch_data,
                                   expected_resp_status=status.HTTP_200_OK,
                                   to_read_from_response='status',
                                   to_check_against=patch_data['status'])

    def test_delete_export(self):
        delete_url = reverse(viewname=self.viewname_detail, args=[self.target_export_to_delete.uuid])
        self.check_test_delete_view(request_user=self.workspaces_manager_user,
                                    delete_url=delete_url,
                                    obj_id=self.target_export_to_delete.uuid,
                                    expected_resp_status=status.HTTP_204_NO_CONTENT)
