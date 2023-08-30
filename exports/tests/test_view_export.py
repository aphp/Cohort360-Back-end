from django.urls import reverse
from rest_framework import status

from exports.models import Export, Datalab
from exports.tests.base_test import ExportsTestBase
from exports.types import ExportType, ExportStatus
from exports.views import ExportViewSet


class ExportViewSetTest(ExportsTestBase):
    view_set = ExportViewSet
    view_root = "exports:v1:exports"
    model = Export

    def setUp(self):
        super().setUp()
        self.datalab = Datalab.objects.create(infrastructure_provider=self.infra_provider_aphp)
        self.csv_export_basic_data = {"name": "Special Export",
                                      "output_format": ExportType.CSV.name,
                                      "owner": self.csv_exporter_user.pk,
                                      "status": ExportStatus.PENDING.name,
                                      "target_name": "12345_09092023_151500",
                                      "export_tables": [{"name": "Some export table"}]
                                      }
        self.exports = [Export.objects.create(**dict(name=f"Export_{i}",
                                                     output_format=ExportType.CSV.name,
                                                     owner=self.csv_exporter_user,
                                                     status=ExportStatus.PENDING.name,
                                                     target_name="12345_09092023_151500"
                                                     )) for i in range(5)]
        self.target_export_to_retrieve = self.exports[0]
        self.target_export_to_patch = self.exports[1]
        self.target_export_to_delete = self.exports[2]

    def test_list_exports(self):
        list_url = reverse(viewname=self.viewname_list)
        self.check_test_list_view(list_url=list_url,
                                  request_user=self.datalabs_reader_user,
                                  expected_resp_status=status.HTTP_200_OK,
                                  result_count=len(self.exports)-1)

    def test_retrieve_export(self):
        retrieve_url = reverse(viewname=self.viewname_detail, args=[self.target_export_to_retrieve.uuid])
        self.check_test_retrieve_view(request_user=self.datalabs_reader_user,
                                      retrieve_url=retrieve_url,
                                      obj_id=self.target_export_to_retrieve.uuid,
                                      expected_resp_status=status.HTTP_200_OK,
                                      to_read_from_response='name',
                                      to_check_against=self.target_export_to_retrieve.name)

    def test_create_export_success(self):
        create_url = reverse(viewname=self.viewname_list)
        self.check_test_create_view(request_user=self.csv_exporter_user,
                                    create_url=create_url,
                                    request_data=self.csv_export_basic_data,
                                    expected_resp_status=status.HTTP_201_CREATED)

    def test_error_create_export_with_no_right(self):
        create_url = reverse(viewname=self.viewname_list)
        self.check_test_create_view(request_user=self.user_without_rights,
                                    create_url=create_url,
                                    request_data=self.csv_export_basic_data,
                                    expected_resp_status=status.HTTP_403_FORBIDDEN)

    def test_patch_export(self):
        patch_url = reverse(viewname=self.viewname_detail, args=[self.target_export_to_patch.uuid])
        patch_data = {'status': ExportStatus.DELIVERED.name}
        self.check_test_patch_view(request_user=self.csv_exporter_user,
                                   patch_url=patch_url,
                                   obj_id=self.target_export_to_patch.uuid,
                                   request_data=patch_data,
                                   expected_resp_status=status.HTTP_200_OK,
                                   to_read_from_response='status',
                                   to_check_against=patch_data['status'])

    def test_delete_export(self):
        delete_url = reverse(viewname=self.viewname_detail, args=[self.target_export_to_delete.uuid])
        self.check_test_delete_view(request_user=self.csv_exporter_user,
                                    delete_url=delete_url,
                                    obj_id=self.target_export_to_delete.uuid,
                                    expected_resp_status=status.HTTP_204_NO_CONTENT)