from unittest import mock

from django.test.utils import override_settings
from django.urls import reverse
from requests.exceptions import RequestException
from rest_framework import status

from admin_cohort.permissions import IsAuthenticated
from admin_cohort.types import JobStatus
from cohort.models import CohortResult, FhirFilter
from exporters.apis.base import BaseAPI
from exporters.enums import APIJobStatus
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
        self.failed_export.request_job_id = "some_job_id"
        self.failed_export.request_job_status = JobStatus.failed
        self.failed_export.save()

        self.finished_export = self.exports[4]
        self.finished_export.request_job_status = JobStatus.finished
        self.finished_export.request_job_id = "some_job_id"
        self.finished_export.save()

        self.retry_view = self.view_set.as_view({'post': 'retry'})
        self.retry_url = f"/exports/{self.failed_export.uuid}/retry/"
        self.logs_view = self.view_set.as_view({'get': 'logs'})

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

    @mock.patch.object(BaseAPI, "get_export_logs")
    @mock.patch.object(ExportViewSet, "get_object")
    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_get_logs_for_failed_export(self, mock_get_object, mock_logs_response):
        mock_get_object.return_value = self.failed_export
        mock_logs_response.return_value = {"status": APIJobStatus.FinishedWithError,
                                           "stdout": "logs for failed export",
                                           "stderr": ""
                                           }
        request = self.make_request(url=f"/exports/{self.failed_export.uuid}/logs/", http_verb="get", request_user=self.admin_user)
        self.logs_view.kwargs = {'uuid': self.failed_export.uuid}
        response = self.logs_view(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.headers['content-type'], 'application/json')

    @mock.patch.object(BaseAPI, "get_export_logs")
    @mock.patch.object(ExportViewSet, "get_object")
    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_get_logs_for_failed_export_api_error(self, mock_get_object, mock_logs_response):
        mock_get_object.return_value = self.failed_export
        mock_logs_response.side_effect = RequestException()
        request = self.make_request(url=f"/exports/{self.failed_export.uuid}/logs/", http_verb="get", request_user=self.admin_user)
        self.logs_view.kwargs = {'uuid': self.failed_export.uuid}
        response = self.logs_view(request)
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertIsNotNone(response.data)

    @mock.patch.object(BaseAPI, "get_export_logs")
    @mock.patch.object(ExportViewSet, "get_object")
    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_get_logs_for_failed_export_api_timeout(self, mock_get_object, mock_logs_response):
        mock_get_object.return_value = self.failed_export
        mock_logs_response.side_effect = TimeoutError()
        request = self.make_request(url=f"/exports/{self.failed_export.uuid}/logs/", http_verb="get", request_user=self.admin_user)
        self.logs_view.kwargs = {'uuid': self.failed_export.uuid}
        response = self.logs_view(request)
        self.assertEqual(response.status_code, status.HTTP_408_REQUEST_TIMEOUT)
        self.assertIsNotNone(response.data)

    @mock.patch.object(ExportViewSet, "get_object")
    def test_get_logs_for_export_missing_job_id(self, mock_get_object):
        export_missing_job_id = self.exports[0]
        mock_get_object.return_value = export_missing_job_id
        request = self.make_request(url=f"/exports/{export_missing_job_id.uuid}/logs/", http_verb="get", request_user=self.admin_user)
        self.logs_view.kwargs = {'uuid': export_missing_job_id.uuid}
        response = self.logs_view(request)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIsNotNone(response.data)

    @mock.patch.object(ExportViewSet, "get_object")
    def test_get_logs_for_finished_export(self, mock_get_object):
        mock_get_object.return_value = self.finished_export
        request = self.make_request(url=f"/exports/{self.finished_export.uuid}/logs/", http_verb="get", request_user=self.admin_user)
        self.logs_view.kwargs = {'uuid': self.finished_export.uuid}
        response = self.logs_view(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(response.data)

    def test_retry_export_as_non_admin_user(self):
        request = self.make_request(url=self.retry_url, http_verb="post", request_user=self.exporter_user)
        self.retry_view.kwargs = {'uuid': self.failed_export.uuid}
        response = self.retry_view(request)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @mock.patch('exports.views.export.export_service')
    @mock.patch.object(ExportViewSet, "get_object")
    def test_retry_failed_export_success(self, mock_get_object, mock_export_service):
        mock_get_object.return_value = self.failed_export
        request = self.make_request(url=self.retry_url, http_verb="post", request_user=self.admin_user)
        self.retry_view.kwargs = {'uuid': self.failed_export.uuid}
        response = self.retry_view(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_export_service.retry.assert_called_once()

    @mock.patch.object(ExportViewSet, "get_object")
    def test_retry_finished_export_fail(self, mock_get_object):
        mock_get_object.return_value = self.finished_export
        retry_url_finished = f"/exports/{self.finished_export.uuid}/retry/"
        request = self.make_request(url=retry_url_finished, http_verb="post", request_user=self.admin_user)
        self.retry_view.kwargs = {'uuid': self.finished_export.uuid}
        response = self.retry_view(request)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
