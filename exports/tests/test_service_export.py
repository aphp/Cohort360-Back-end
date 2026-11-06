from unittest import mock

from admin_cohort.types import JobStatus
from cohort.models import CohortResult, FhirFilter, Folder, Request, RequestQuerySnapshot
from exports.enums import ExportPurpose
from exports.models import Export, ExportTable
from exports.services.export import export_service, TABLES_REQUIRING_SUB_COHORTS, EXCLUDED_TABLES
from exports.tests.test_view_export_request import ExportsTests


class TestServiceExport(ExportsTests):
    def setUp(self):
        super().setUp()
        self.basic_export_data = dict(output_format="csv", nominative=True, motivation="motivation")
        self.basic_export = Export.objects.create(**self.basic_export_data, owner=self.user1)
        for i in range(3):
            cr = CohortResult.objects.create(is_subset=True, name=f"cohort subset {i}", owner=self.user1, request_job_status=JobStatus.finished)
            ExportTable.objects.create(export=self.basic_export, cohort_result_subset=cr)

        self.second_export = Export.objects.create(**self.basic_export_data, owner=self.user2)
        self.main_cohort = CohortResult.objects.create(name="cohort of user2", owner=self.user2, request_job_status=JobStatus.finished)
        self.fhir_filter = FhirFilter.objects.create(fhir_resource="Patient", filter="param=value", name="patient filter", owner=self.user2)

    @mock.patch("exports.services.export.launch_export_task.delay")
    def test_export_is_launched_after_check_all_cohort_subsets_created(self, mock_launch_export_task):
        mock_launch_export_task.return_value = None
        export_service.check_all_cohort_subsets_created(export=self.basic_export)
        mock_launch_export_task.assert_called_once_with(self.basic_export.pk)

    @mock.patch("exports.services.export.launch_export_task.delay")
    @mock.patch("exporters.exporters.base_exporter.notify_export_failed.delay")
    def test_export_is_not_launched_if_some_cohort_subset_failed(self, mock_notify_export_failed_task, mock_launch_export_task):
        mock_notify_export_failed_task.return_value = None
        mock_launch_export_task.return_value = None
        cr = CohortResult.objects.create(is_subset=True, name="failed cohort subset", owner=self.user1, request_job_status=JobStatus.failed)
        ExportTable.objects.create(export=self.basic_export, cohort_result_subset=cr)
        export_service.check_all_cohort_subsets_created(export=self.basic_export)
        self.assertEqual(self.basic_export.request_job_status, JobStatus.failed.value)
        self.assertIsNotNone(self.basic_export.request_job_fail_msg)
        mock_notify_export_failed_task.assert_called_once()
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
        tables = [
            {
                "table_name": "Patient",
                "cohort_result_source": self.main_cohort.uuid,
                "fhir_filter": self.fhir_filter.uuid,
            }
        ]
        requires_cohort_subsets = export_service.create_tables(export=self.second_export, tables=tables)
        mock_create_cohort_subset.assert_called_once()
        self.assertTrue(requires_cohort_subsets)

    @mock.patch("exports.services.export.cohort_service.create_cohort_subset")
    def test_force_create_cohort_subsets_without_filter_when_create_tables(self, mock_create_cohort_subset):
        mock_create_cohort_subset.return_value = None
        tables = [{"table_name": TABLES_REQUIRING_SUB_COHORTS[0], "cohort_result_source": self.main_cohort.uuid}]
        requires_cohort_subsets = export_service.create_tables(export=self.second_export, tables=tables)
        mock_create_cohort_subset.assert_called_once()
        self.assertTrue(requires_cohort_subsets)

    @mock.patch("exports.services.export.cohort_service.create_cohort_subset")
    def test_not_create_cohort_subsets_when_create_tables(self, mock_create_cohort_subset):
        mock_create_cohort_subset.return_value = None
        tables = [{"table_name": EXCLUDED_TABLES[0], "cohort_result_source": self.main_cohort.uuid}]
        requires_cohort_subsets = export_service.create_tables(export=self.second_export, tables=tables)
        mock_create_cohort_subset.assert_not_called()
        self.assertFalse(requires_cohort_subsets)


class TestPrefillReferenceExport(ExportsTests):
    def setUp(self):
        super().setUp()
        folder = Folder.objects.create(name="folder", owner=self.user1)
        request = Request.objects.create(name="request", owner=self.user1, parent_folder=folder)
        self.snapshot = self.create_snapshot(request)
        self.other_snapshot = self.create_snapshot(request)
        self.cohort = self.create_cohort(self.snapshot)

    def create_snapshot(self, request):
        return RequestQuerySnapshot.objects.create(owner=self.user1, request=request, serialized_query="{}", perimeters_ids=["1"])

    def create_cohort(self, snapshot=None, parent_cohort=None):
        return CohortResult.objects.create(
            name="cohort", owner=self.user1, request_query_snapshot=snapshot, parent_cohort=parent_cohort, request_job_status=JobStatus.finished
        )

    def create_export(self, cohort, owner=None, purpose=ExportPurpose.CARE_SUPPORT.value):
        export = Export.objects.create(output_format="csv", owner=owner or self.user1, purpose=purpose)
        ExportTable.objects.create(export=export, name="Patient", cohort_result_source=cohort)
        return export

    def get_reference(self, cohort):
        return export_service.get_prefill_reference_export(cohort=cohort, user=self.user1)

    def test_reference_is_the_cohort_export(self):
        export = self.create_export(self.cohort)
        self.assertEqual(self.get_reference(self.cohort), export)

    def test_reference_is_the_latest_export_of_the_cohort(self):
        self.create_export(self.cohort)
        latest_export = self.create_export(self.cohort)
        self.assertEqual(self.get_reference(self.cohort), latest_export)

    def test_reference_falls_back_on_a_cohort_of_the_same_snapshot(self):
        export = self.create_export(self.create_cohort(self.snapshot))
        self.assertEqual(self.get_reference(self.cohort), export)

    def test_reference_falls_back_on_another_version_of_the_request(self):
        export = self.create_export(self.create_cohort(self.other_snapshot))
        self.assertEqual(self.get_reference(self.cohort), export)

    def test_cohort_export_takes_priority_over_a_more_recent_request_export(self):
        export = self.create_export(self.cohort)
        self.create_export(self.create_cohort(self.other_snapshot))
        self.assertEqual(self.get_reference(self.cohort), export)

    def test_sample_uses_its_parent_export(self):
        export = self.create_export(self.cohort)
        sample = self.create_cohort(self.snapshot, parent_cohort=self.cohort)
        self.assertEqual(self.get_reference(sample), export)

    def test_parent_uses_its_sample_export(self):
        sample = self.create_cohort(self.snapshot, parent_cohort=self.cohort)
        export = self.create_export(sample)
        self.assertEqual(self.get_reference(self.cohort), export)

    def test_sample_uses_the_export_of_another_sample(self):
        sample = self.create_cohort(parent_cohort=self.cohort)
        other_sample = self.create_cohort(parent_cohort=self.cohort)
        export = self.create_export(other_sample)
        self.assertEqual(self.get_reference(sample), export)

    def test_export_of_another_user_is_ignored(self):
        self.create_export(self.cohort, owner=self.user2)
        self.assertIsNone(self.get_reference(self.cohort))

    def test_export_without_purpose_is_ignored(self):
        self.create_export(self.cohort, purpose=None)
        self.assertIsNone(self.get_reference(self.cohort))

    def test_no_reference_when_the_request_was_never_exported(self):
        self.assertIsNone(self.get_reference(self.cohort))

    def test_no_reference_for_a_cohort_without_snapshot(self):
        self.assertIsNone(self.get_reference(self.create_cohort()))
