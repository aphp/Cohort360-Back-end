from unittest import mock

from django.http import HttpRequest
from django.test import TestCase

from admin_cohort.tests.tests_tools import new_random_user
from cohort.models import Folder, Request, RequestQuerySnapshot, CohortResult, DatedMeasure, FhirFilter
from cohort.services.cohort_result import CohortResultService


class TestCohortResultService(TestCase):

    def setUp(self):
        super().setUp()
        self.user1 = new_random_user()
        self.folder = Folder.objects.create(owner=self.user1, name="f1")
        self.request = Request.objects.create(owner=self.user1,
                                              name="Request 1",
                                              description="Request 1",
                                              parent_folder=self.folder)
        self.rqs = RequestQuerySnapshot.objects.create(owner=self.user1,
                                                       request=self.request,
                                                       serialized_query='{}')
        self.dm = DatedMeasure.objects.create(owner=self.user1,
                                              request_query_snapshot=self.rqs)
        self.source_cohort = CohortResult.objects.create(owner=self.user1,
                                                         request_query_snapshot=self.rqs,
                                                         dated_measure=self.dm)
        self.fhir_filter = FhirFilter.objects.create(owner=self.user1,
                                                     fhir_resource="Resource",
                                                     name="Filter_01",
                                                     filter="param=value")
        self.cohort_result_service = CohortResultService()

    @mock.patch('cohort.services.cohort_result.get_authorization_header')
    @mock.patch('cohort.services.cohort_result.create_cohort_task.delay')
    def test_create_cohort_subset(self, mock_get_auth_headers, mock_celery_task):
        mock_get_auth_headers.return_value = {"authorization": "token"}
        mock_celery_task.return_value = None
        cohort_subset = self.cohort_result_service.create_cohort_subset(http_request=HttpRequest(),
                                                                        owner_id=self.user1.pk,
                                                                        table_name="Table_01",
                                                                        source_cohort=self.source_cohort,
                                                                        fhir_filter_id=self.fhir_filter.pk)
        self.assertNotEqual(self.source_cohort.pk, cohort_subset.pk)
        self.assertNotEqual(self.source_cohort.dated_measure.pk, cohort_subset.dated_measure.pk)

