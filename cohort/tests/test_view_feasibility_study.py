from unittest import mock

from django.test import TestCase
from django.urls import reverse
from rest_framework import status

from accesses.models import Perimeter
from admin_cohort.tests.tests_tools import PatchCase, FileDownloadCase
from admin_cohort.types import JobStatus
from cohort.models import RequestQuerySnapshot, Request, Folder, FeasibilityStudy
from cohort.services.feasibility_study import feasibility_study_service
from cohort.tests.cohort_app_tests import CohortAppTests
from cohort.views import FeasibilityStudyViewSet


class FeasibilityStudyViewTests(CohortAppTests):
    objects_url = "/feasibility-studies/"
    retrieve_view = FeasibilityStudyViewSet.as_view({'get': 'retrieve'})
    list_view = FeasibilityStudyViewSet.as_view({'get': 'list'})
    create_view = FeasibilityStudyViewSet.as_view({'post': 'create'})
    update_view = FeasibilityStudyViewSet.as_view({'patch': 'partial_update'})
    download_view = FeasibilityStudyViewSet.as_view(actions={'get': 'download_report'})
    model = FeasibilityStudy
    model_objects = FeasibilityStudy.objects
    model_fields = FeasibilityStudy._meta.fields

    def setUp(self):
        super().setUp()
        self.folder = Folder.objects.create(owner=self.user1, name="f1")
        self.request = Request.objects.create(owner=self.user1,
                                              name="Request 1",
                                              description="Request 1 from user 1",
                                              parent_folder=self.folder)
        self.rqs = RequestQuerySnapshot.objects.create(owner=self.user1,
                                                       request=self.request,
                                                       serialized_query='{}')
        self.basic_data = dict(request_query_snapshot_id=self.rqs.pk,
                               owner=self.user1)

    @mock.patch('cohort.services.feasibility_study.get_template')
    @mock.patch('cohort.services.feasibility_study.send_email_feasibility_report_ready.apply_async')
    @mock.patch('cohort.services.feasibility_study.FeasibilityStudyService.build_feasibility_report')
    @mock.patch('cohort_job_server.cohort_counter.CohortCounter.handle_patch_feasibility_study')
    def test_successfully_patch_feasibility_study(self, mock_patch_handler, mock_build_report, mock_send_email_report_ready, mock_get_template):
        extra = {group_id: count for (group_id, count) in [("1", "10"), ("2", "10"), ("3", "10"),
                                                           ("4", "15"), ("5", "15"), ("6", "25")]}
        mock_patch_handler.return_value = JobStatus.finished, extra
        mock_build_report.return_value = {"1111": 1111}, "<html><body><h1>Some HTML</h1></body></html>"
        mock_send_email_report_ready.return_value = None
        mock_get_template.render.return_value = ''

        patch_data = {"request_job_status": "finished",
                      "count": 25,
                      "extra": extra
                      }
        case = PatchCase(initial_data=self.basic_data,
                         data_to_update=patch_data,
                         user=self.user1,
                         status=status.HTTP_200_OK,
                         success=True)
        response_data = self.check_patch_case(case, check_fields_updated=False, return_response_data=True)
        mock_patch_handler.assert_called()
        mock_build_report.assert_called()
        mock_send_email_report_ready.assert_called()
        feasibility_study_id = response_data['uuid']
        feasibility_study = FeasibilityStudy.objects.get(pk=feasibility_study_id)
        self.assertIsNotNone(feasibility_study.report_json_content)
        self.assertIsNotNone(feasibility_study.report_file)

    @mock.patch('cohort.services.feasibility_study.send_email_feasibility_report_error.apply_async')
    @mock.patch('cohort_job_server.cohort_counter.CohortCounter.handle_patch_feasibility_study')
    def test_error_patch_feasibility_study(self, mock_patch_handler, mock_send_email_report_error):
        mock_patch_handler.side_effect = ValueError("Wrong value for status")
        mock_send_email_report_error.return_value = None
        case = PatchCase(initial_data=self.basic_data,
                         data_to_update={"request_job_status": "INVALID_STATUS",},
                         user=self.user1,
                         status=status.HTTP_400_BAD_REQUEST,
                         success=False)
        self.check_patch_case(case)
        mock_patch_handler.assert_called()
        mock_send_email_report_error.assert_called()

    def test_download_report(self):
        html_report = "<html><body><p>some content</p></body></html>"
        f_study = FeasibilityStudy.objects.create(**self.basic_data,
                                                  report_file=str.encode(html_report))
        url = reverse(viewname="cohort:feasibility-studies-download-report", args=[f_study.uuid])
        base_case = FileDownloadCase(url=url,
                                     view_params=dict(uuid=f_study.uuid),
                                     expected_content_type=None,
                                     user=self.user1,
                                     success=True,
                                     status=status.HTTP_200_OK)
        success_case = base_case.clone(expected_content_type="application/zip")
        self.check_file_download_case(case=success_case, download_view=self.__class__.download_view)

        f_study.report_file = None
        f_study.save()
        error_case = base_case.clone(success=False,
                                     status=status.HTTP_404_NOT_FOUND)
        self.check_file_download_case(case=error_case, download_view=self.__class__.download_view)


class TestFeasibilityStudiesService(TestCase):

    def setUp(self):
        super().setUp()
        self.create_perimeters_tree()
        self.counts_per_perimeter = {cohort_id: count for (cohort_id, count) in [("1", "25"), ("2", "10"), ("3", "10"), ("4", "15"), ("5", "15")]}

    @staticmethod
    def create_perimeters_tree():
        basic_data = [
            {'id': 1, 'name': 'APHP', 'type_source_value': 'TYPE0', 'cohort_id': '1', 'local_id': '1', 'parent_id': None, 'level': 1},
            {'id': 2, 'name': 'GHU-01', 'type_source_value': 'TYPE1', 'cohort_id': '2', 'local_id': '2', 'parent_id': 1, 'level': 2},
            {'id': 3, 'name': 'Hop-01', 'type_source_value': 'TYPE2', 'cohort_id': '3', 'local_id': '3', 'parent_id': 2, 'level': 3},
            {'id': 4, 'name': 'Pole/DMU-01', 'type_source_value': 'TYPE3', 'cohort_id': '4', 'local_id': '4', 'parent_id': 3, 'level': 4},
            {'id': 5, 'name': 'UF-01', 'type_source_value': 'TYPE4', 'cohort_id': '5', 'local_id': '5', 'parent_id': 4,
             'level': 5},
            {'id': 6, 'name': 'UC-01', 'type_source_value': 'TYPE5', 'cohort_id': '6', 'local_id': '6', 'parent_id': 5,
             'level': 6}]
        for d in basic_data:
            Perimeter.objects.create(**d)

    def test_build_feasibility_report(self):
        json_content, html_content = feasibility_study_service.build_feasibility_report(counts_per_perimeter=self.counts_per_perimeter)
        self.assertEqual(html_content.count('<li'), len(self.counts_per_perimeter))
        self.assertEqual(html_content.count('<input'), len(self.counts_per_perimeter))
        self.assertEqual(len(json_content), len(self.counts_per_perimeter))
