from django.urls import reverse
from rest_framework import status

from admin_cohort.types import JobStatus
from cohort.models import CohortResult, FhirFilter
from exports.models import Export, Datalab
from exports.tests.base_test import ExportsTestBase
from exports.enums import ExportStatus
from exports.views import ExportViewSet


class ExportViewSetTest(ExportsTestBase):
    view_set = ExportViewSet
    view_root = "exports:v1:exports"
    model = Export

    def setUp(self):
        super().setUp()
        self.datalab = Datalab.objects.create(name="main_datalab", infrastructure_provider=self.infra_provider_aphp)
        self.cohort_result = CohortResult.objects.create(name="Cohort For Export Purposes",
                                                         owner=self.exporter_user,
                                                         request_query_snapshot=self.rqs,
                                                         request_job_status=JobStatus.finished)
        self.fhir_filter = FhirFilter.objects.create(name="Some FHIR Filter",
                                                     owner=self.exporter_user,
                                                     fhir_resource="some_resource",
                                                     filter="some_filter")
        self.export_basic_data = {"name": "Special Export",
                                  "output_format": self.export_type,
                                  "nominative": True,
                                  "owner": self.exporter_user.pk,
                                  "status": ExportStatus.PENDING.name,
                                  "export_tables": [{"name": "person",
                                                     "cohort_result_source": self.cohort_result.uuid,
                                                     "fhir_filter": self.fhir_filter.uuid}]
                              }
        self.exports = [Export.objects.create(**dict(output_format=self.export_type,
                                                     owner=self.exporter_user,
                                                     status=ExportStatus.PENDING.name,
                                                     target_name="12345_09092023_151500"
                                                     )) for _ in range(5)]
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
                                      to_read_from_response='target_name',
                                      to_check_against=self.target_export_to_retrieve.target_name)

    def test_error_create_export_with_no_right(self):
        create_url = reverse(viewname=self.viewname_list)
        self.check_test_create_view(request_user=self.user_without_rights,
                                    create_url=create_url,
                                    request_data=self.export_basic_data,
                                    expected_resp_status=status.HTTP_403_FORBIDDEN)

    def test_patch_export(self):
        patch_url = reverse(viewname=self.viewname_detail, args=[self.target_export_to_patch.uuid])
        patch_data = {'status': ExportStatus.DELIVERED.name}
        self.check_test_patch_view(request_user=self.exporter_user,
                                   patch_url=patch_url,
                                   obj_id=self.target_export_to_patch.uuid,
                                   request_data=patch_data,
                                   expected_resp_status=status.HTTP_200_OK,
                                   to_read_from_response='status',
                                   to_check_against=patch_data['status'])

    def test_delete_export(self):
        delete_url = reverse(viewname=self.viewname_detail, args=[self.target_export_to_delete.uuid])
        self.check_test_delete_view(request_user=self.exporter_user,
                                    delete_url=delete_url,
                                    obj_id=self.target_export_to_delete.uuid,
                                    expected_resp_status=status.HTTP_204_NO_CONTENT)
