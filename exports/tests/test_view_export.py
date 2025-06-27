from unittest import mock

from django.urls import reverse
from rest_framework import status

from admin_cohort.permissions import IsAuthenticated
from admin_cohort.types import JobStatus
from cohort.models import CohortResult, FhirFilter
from exports.models import Export, Datalab
from exports.tests.base_test import ExportsTestBase
from exports.views import ExportViewSet


class ExportViewSetTest(ExportsTestBase):
    view_set = ExportViewSet
    view_root = "exports:exports"
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
                                  "export_tables": [{"table_name": "person",
                                                     "cohort_result_source": self.cohort_result.uuid,
                                                     "fhir_filter": self.fhir_filter.uuid}]
                                  }
        self.export_data_error = {**self.export_basic_data,
                                  "export_tables": [{"table_name": "person"},
                                                    {"table_name": "table01"},
                                                    {"table_name": "table02"}]
                                  }
        self.exports = [Export.objects.create(**dict(output_format=self.export_type,
                                                     owner=self.exporter_user,
                                                     target_name="12345_09092023_151500"
                                                     )) for _ in range(5)]
        self.target_export_to_retrieve = self.exports[0]
        self.target_export_to_patch = self.exports[1]
        self.target_export_to_delete = self.exports[2]

        self.failed_export = self.exports[3]
        self.failed_export.request_job_status = JobStatus.failed
        self.failed_export.save()
        self.retry_view = self.view_set.as_view({'post': 'retry'})
        self.retry_url = f"/exports/{self.failed_export.uuid}/retry/"

    def test_list_exports(self):
        list_url = reverse(viewname=self.viewname_list)
        self.check_test_list_view(list_url=list_url,
                                  request_user=self.datalabs_reader_user,
                                  expected_resp_status=status.HTTP_200_OK,
                                  result_count=len(self.exports)-1)

    @mock.patch.object(ExportViewSet, 'permission_classes', [IsAuthenticated])
    def test_create_export_success(self):
        create_url = reverse(viewname=self.viewname_list)
        self.check_test_create_view(request_user=self.exporter_user,
                                    create_url=create_url,
                                    request_data=self.export_basic_data,
                                    expected_resp_status=status.HTTP_201_CREATED)

    @mock.patch.object(ExportViewSet, 'permission_classes', [IsAuthenticated])
    def test_create_export_with_pivot_merge_success(self):
        create_url = reverse(viewname=self.viewname_list)
        export_data = {**self.export_basic_data,
                       "export_tables": [{"table_name": "person",
                                          "cohort_result_source": self.cohort_result.uuid,
                                          "pivot_merge": True,
                                          "columns": None
                                          }]
                      }
        self.check_test_create_view(request_user=self.exporter_user,
                                    create_url=create_url,
                                    request_data=export_data,
                                    expected_resp_status=status.HTTP_201_CREATED)

    @mock.patch.object(ExportViewSet, 'permission_classes', [IsAuthenticated])
    def test_create_export_with_pivot_merge_columns_success(self):
        create_url = reverse(viewname=self.viewname_list)
        export_data = {**self.export_basic_data,
                       "export_tables": [{"table_name": "person",
                                          "cohort_result_source": self.cohort_result.uuid,
                                          "pivot_merge_columns": ["col_01", "col_02", "col_03"],
                                          "pivot_merge_ids": ["col_01", "col_02"],
                                          "columns": None
                                          }]
                       }
        self.check_test_create_view(request_user=self.exporter_user,
                                    create_url=create_url,
                                    request_data=export_data,
                                    expected_resp_status=status.HTTP_201_CREATED)

    @mock.patch.object(ExportViewSet, 'permission_classes', [IsAuthenticated])
    def test_create_export_error(self):
        create_url = reverse(viewname=self.viewname_list)
        self.check_test_create_view(request_user=self.exporter_user,
                                    create_url=create_url,
                                    request_data=self.export_data_error,
                                    expected_resp_status=status.HTTP_400_BAD_REQUEST)

    @mock.patch("exports.services.export.launch_export_task.delay")
    @mock.patch.object(ExportViewSet, "get_object")
    def test_successfully_retry_export(self, mock_get_object, mock_task):
        mock_task.return_value = None
        mock_get_object.return_value = self.failed_export
        request = self.make_request(url=self.retry_url, http_verb="post", request_user=self.admin_user)
        self.retry_view.kwargs = {'uuid': self.failed_export.pk}
        response = self.retry_view(request)
        mock_task.assert_called_once_with(self.failed_export.pk)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.failed_export.refresh_from_db()
        self.assertEqual(self.failed_export.request_job_status, JobStatus.new)
        self.assertTrue(self.failed_export.retried)

    @mock.patch("exports.services.export.launch_export_task.delay")
    @mock.patch.object(ExportViewSet, "get_object")
    def test_error_retry_export(self, mock_get_object, mock_task):
        self.failed_export.request_job_status = JobStatus.finished
        mock_get_object.return_value = self.failed_export
        request = self.make_request(url=self.retry_url, http_verb="post", request_user=self.admin_user)
        self.retry_view.kwargs = {'uuid': self.failed_export.pk}
        response = self.retry_view(request)
        mock_task.assert_not_called()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.failed_export.refresh_from_db()
        self.assertEqual(self.failed_export.request_job_status, JobStatus.failed)
        self.assertFalse(self.failed_export.retried)
