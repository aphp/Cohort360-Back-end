from django.urls import reverse
from rest_framework import status

from exports.models import ExportTable, Export, Datalab
from exports.tests.base_test import ExportsTestBase
from exports.types import ExportType, ExportStatus
from exports.views import ExportTableViewSet


class ExportTableViewSetTestBase(ExportsTestBase):
    view_set = ExportTableViewSet
    view_root = "exports:v1:export_tables"
    model = ExportTable

    def setUp(self):
        super().setUp()
        self.datalab = Datalab.objects.create(infrastructure_provider=self.infra_provider_aphp)
        self.export = Export.objects.create(name="Export 01",
                                            output_format=ExportType.CSV,
                                            owner=self.workspaces_manager_user,
                                            datalab=self.datalab,
                                            status=ExportStatus.PENDING,
                                            target_name="12345_09092023_151500")
        self.export_tables = [ExportTable.objects.create(name=f"export_table_{i}",
                                                         export=self.export) for i in range(5)]
        self.target_export_table_to_retrieve = self.export_tables[0]

    def test_list_export_tables(self):
        list_url = reverse(viewname=self.viewname_list)
        self.check_test_list_view(list_url=list_url,
                                  request_user=self.workspaces_reader_user,
                                  expected_resp_status=status.HTTP_200_OK,
                                  result_count=len(self.export_tables)-1)

    def test_retrieve_export_table(self):
        retrieve_url = reverse(viewname=self.viewname_detail, args=[self.target_export_table_to_retrieve.uuid])
        self.check_test_retrieve_view(request_user=self.workspaces_reader_user,
                                      retrieve_url=retrieve_url,
                                      obj_id=self.target_export_table_to_retrieve.uuid,
                                      expected_resp_status=status.HTTP_200_OK,
                                      to_read_from_response='name',
                                      to_check_against=self.target_export_table_to_retrieve.name)
