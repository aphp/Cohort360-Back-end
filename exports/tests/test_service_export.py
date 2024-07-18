from unittest import mock

from admin_cohort.types import JobStatus
from cohort.models import CohortResult, FhirFilter
from exports.models import Export, ExportTable
from exports.services.export import export_service, TABLES_REQUIRING_SUB_COHORTS, EXCLUDED_TABLES
from exports.tests.test_view_export_request import ExportsTests


class TestServiceExport(ExportsTests):

    def setUp(self):
        super().setUp()
        self.basic_export_data = dict(output_format="plain",
                                      nominative=True,
                                      motivation='motivation')
        self.basic_export = Export.objects.create(**self.basic_export_data,
                                                  owner=self.user1)
        for i in range(3):
            cr = CohortResult.objects.create(is_subset=True,
                                             name=f'cohort subset {i}',
                                             owner=self.user1,
                                             request_job_status=JobStatus.finished)
            ExportTable.objects.create(export=self.basic_export, cohort_result_subset=cr)

        self.second_export = Export.objects.create(**self.basic_export_data,
                                                   owner=self.user2)
        self.main_cohort = CohortResult.objects.create(name='cohort of user2',
                                                       owner=self.user2,
                                                       request_job_status=JobStatus.finished)
        self.fhir_filter = FhirFilter.objects.create(fhir_resource='Patient',
                                                     filter='param=value',
                                                     name='patient filter',
                                                     owner=self.user2)

    @mock.patch("exports.services.export.launch_export_task.delay")
    def test_export_is_launched_after_check_all_cohort_subsets_created(self, mock_launch_export_task):
        mock_launch_export_task.return_value = None
        export_service.check_all_cohort_subsets_created(export=self.basic_export)
        mock_launch_export_task.assert_called_once_with(self.basic_export.pk)

    @mock.patch("exports.services.export.launch_export_task.delay")
    def test_export_is_not_launched_if_some_cohort_subset_failed(self, mock_launch_export_task):
        mock_launch_export_task.return_value = None
        cr = CohortResult.objects.create(is_subset=True,
                                         name='failed cohort subset',
                                         owner=self.user1,
                                         request_job_status=JobStatus.failed)
        ExportTable.objects.create(export=self.basic_export, cohort_result_subset=cr)
        export_service.check_all_cohort_subsets_created(export=self.basic_export)
        self.assertEqual(self.basic_export.request_job_status, JobStatus.failed.value)
        self.assertIsNotNone(self.basic_export.request_job_fail_msg)
        mock_launch_export_task.assert_not_called()

    @mock.patch("exports.services.export.launch_export_task.delay")
    def test_export_is_not_launched_if_some_cohort_subset_is_pending(self, mock_launch_export_task):
        mock_launch_export_task.return_value = None
        self.basic_export.export_tables.filter(cohort_result_subset__request_job_status=JobStatus.failed.value).delete()
        related_cohort = self.basic_export.export_tables.first().cohort_result_subset
        related_cohort.request_job_status = JobStatus.long_pending.value
        related_cohort.save()
        export_service.check_all_cohort_subsets_created(export=self.basic_export)
        mock_launch_export_task.assert_not_called()

    @mock.patch("exports.services.export.cohort_service.create_cohort_subset")
    def test_create_cohort_subsets_when_create_tables(self, mock_create_cohort_subset):
        mock_create_cohort_subset.return_value = None
        tables = [{'table_ids': ['person'],
                   'cohort_result_source': self.main_cohort.uuid,
                   'fhir_filter': self.fhir_filter.uuid,
                   }]
        requires_cohort_subsets = export_service.create_tables(export=self.second_export, tables=tables)
        mock_create_cohort_subset.assert_called_once()
        self.assertTrue(requires_cohort_subsets)

    @mock.patch("exports.services.export.cohort_service.create_cohort_subset")
    def test_force_create_cohort_subsets_without_filter_when_create_tables(self, mock_create_cohort_subset):
        mock_create_cohort_subset.return_value = None
        tables = [{'table_ids': [TABLES_REQUIRING_SUB_COHORTS[0]],
                   'cohort_result_source': self.main_cohort.uuid
                   }]
        requires_cohort_subsets = export_service.create_tables(export=self.second_export, tables=tables)
        mock_create_cohort_subset.assert_called_once()
        self.assertTrue(requires_cohort_subsets)

    @mock.patch("exports.services.export.cohort_service.create_cohort_subset")
    def test_not_create_cohort_subsets_when_create_tables(self, mock_create_cohort_subset):
        mock_create_cohort_subset.return_value = None
        tables = [{'table_ids': [EXCLUDED_TABLES[0]],
                   'cohort_result_source': self.main_cohort.uuid
                   }]
        requires_cohort_subsets = export_service.create_tables(export=self.second_export, tables=tables)
        mock_create_cohort_subset.assert_not_called()
        self.assertFalse(requires_cohort_subsets)



