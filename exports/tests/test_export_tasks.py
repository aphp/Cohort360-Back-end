from unittest.mock import patch

from django.test import TestCase, override_settings

from admin_cohort.tests.tests_tools import new_user_and_profile
from admin_cohort.types import JobStatus
from cohort.models import FhirFilter, CohortResult
from exporters.exporters.base_exporter import BaseExporter
from exporters.exporters.hive_exporter import HiveExporter
from exports.export_tasks import relaunch_cohort_subsets, await_cohort_subsets, prepare_export, send_export_request
from exports.models import Export, InfrastructureProvider, Datalab, ExportTable
from exports.services.export import export_service


@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
class ExportTasksChainTestCase(TestCase):

    def setUp(self):
        super().setUp()
        self.export_user, _ = new_user_and_profile()
        self.datalab = Datalab.objects.create(name="test_datalab",
                                              infrastructure_provider=InfrastructureProvider.objects.create(name="provider"))
        base_export_data = dict(owner=self.export_user,
                                motivation="motivation",
                                nominative=True,
                                target_name="some_target_name")
        self.csv_export = Export.objects.create(**base_export_data, output_format="csv")
        self.hive_export = Export.objects.create(**base_export_data, output_format="hive", datalab=self.datalab)
        self.fhir_filter = FhirFilter.objects.create(fhir_resource="some_resource",
                                                     filter="param=value",
                                                     name="test_filter",
                                                     owner=self.export_user
                                                     )
        self.cohort = CohortResult.objects.create(name='cohort',
                                                  owner=self.export_user,
                                                  request_job_status=JobStatus.finished)
        self.cohort_subset = CohortResult.objects.create(name='cohort subset',
                                                         owner=self.export_user,
                                                         request_job_status=JobStatus.finished,
                                                         is_subset=True)

    @patch("exports.export_tasks.notify_succeeded.push_email_notification")
    @patch.object(target=BaseExporter, attribute="track_job")
    @patch.object(target=BaseExporter, attribute="send_export")
    @patch("exports.export_tasks.await_cohorts.time.sleep")
    @patch("exports.export_tasks.create_cohorts.cohort_service.create_cohort_subset")
    @patch("exports.export_tasks.notify_received.push_email_notification")
    def test_run_all_tasks_for_csv_export(self,
                                          mock_push_reception_notif,
                                          mock_create_cohort_subset,
                                          mock_sleep,
                                          mock_send_export,
                                          mock_track_job,
                                          mock_push_success_notif):
        mock_push_reception_notif.return_value = None
        mock_push_success_notif.return_value = None
        mock_create_cohort_subset.return_value = self.cohort_subset
        mock_sleep.return_value = None
        mock_send_export.return_value = "some-valid-job-id"
        mock_track_job.return_value = JobStatus.finished

        tables_data = [dict(table_name="person",
                            cohort_result_source=self.cohort.uuid,
                            fhir_filter=self.fhir_filter.uuid,
                            columns=["col_01", "col_02"],
                            pivot_merge=True,
                            pivot_merge_columns=["col_01", "col_02"],
                            pivot_merge_ids=["id_01", "id_02"]),
                       dict(table_name="some_table",
                            cohort_result_source=self.cohort.uuid,
                            fhir_filter=self.fhir_filter.uuid,
                            columns=["col_01", "col_02"],
                            pivot_merge=True,
                            pivot_merge_columns=["col_01", "col_02"],
                            pivot_merge_ids=["id_01", "id_02"]),
                       ]
        result = export_service.proceed_with_export(export=self.csv_export, tables=tables_data, auth_headers={})

        mock_push_reception_notif.assert_called_once()
        self.assertEqual(mock_create_cohort_subset.call_count, len(tables_data))
        mock_push_success_notif.assert_called_once()
        self.assertTrue(result)

    @patch("exports.export_tasks.notify_succeeded.push_email_notification")
    @patch.object(target=BaseExporter, attribute="track_job")
    @patch.object(target=BaseExporter, attribute="send_export")
    @patch.object(target=HiveExporter, attribute="change_db_ownership")
    @patch.object(target=HiveExporter, attribute="create_db")
    @patch("exports.export_tasks.await_cohorts.time.sleep")
    @patch("exports.export_tasks.create_cohorts.cohort_service.create_cohort_subset")
    @patch("exports.export_tasks.notify_received.push_email_notification")
    def test_run_all_tasks_for_hive_export(self,
                                           mock_push_reception_notif,
                                           mock_create_cohort_subset,
                                           mock_sleep,
                                           mock_create_db,
                                           mock_change_db_ownership,
                                           mock_send_export,
                                           mock_track_job,
                                           mock_push_success_notif):
        mock_push_reception_notif.return_value = None
        mock_push_success_notif.return_value = None
        mock_create_cohort_subset.return_value = self.cohort_subset
        mock_sleep.return_value = None
        mock_create_db.return_value = None
        mock_change_db_ownership.return_value = None
        mock_send_export.return_value = "some-valid-job-id"
        mock_track_job.return_value = JobStatus.finished

        tables_data = [dict(table_name="person",
                            cohort_result_source=self.cohort.uuid,
                            fhir_filter=self.fhir_filter.uuid),
                       dict(table_name="some_table",
                            cohort_result_source=self.cohort.uuid,
                            fhir_filter=self.fhir_filter.uuid)
                       ]
        result = export_service.proceed_with_export(export=self.hive_export, tables=tables_data, auth_headers={})

        mock_push_reception_notif.assert_called_once()
        self.assertEqual(mock_create_cohort_subset.call_count, len(tables_data))
        mock_create_db.assert_called_once()
        self.assertEqual(mock_change_db_ownership.call_count, 2)
        mock_push_success_notif.assert_called_once()
        self.assertTrue(result)

    @patch("exports.export_tasks.notify_succeeded.push_email_notification")
    @patch.object(target=BaseExporter, attribute="track_job")
    @patch.object(target=BaseExporter, attribute="send_export")
    @patch("exports.export_tasks.await_cohorts.time.sleep")
    @patch("exports.export_tasks.create_cohorts.cohort_service.create_cohort_subset")
    @patch("exports.export_tasks.notify_received.push_email_notification")
    def test_csv_export_without_creating_cohort_subsets(self,
                                                        mock_push_reception_notif,
                                                        mock_create_cohort_subset,
                                                        mock_sleep,
                                                        mock_send_export,
                                                        mock_track_job,
                                                        mock_push_success_notif):
        mock_push_reception_notif.return_value = None
        mock_push_success_notif.return_value = None
        mock_send_export.return_value = "some-valid-job-id"
        mock_track_job.return_value = JobStatus.finished

        tables_data = [dict(table_name="person",
                            cohort_result_source=self.cohort.uuid)
                       ]
        result = export_service.proceed_with_export(export=self.csv_export, tables=tables_data, auth_headers={})

        mock_push_reception_notif.assert_called_once()
        mock_create_cohort_subset.assert_not_called()
        mock_sleep.assert_not_called()
        mock_send_export.assert_called_once()
        mock_track_job.assert_called_once()
        mock_push_success_notif.assert_called_once()
        self.assertTrue(result)

    @patch("exports.export_tasks.notify_failed.push_email_notification")
    @patch("exports.export_tasks.notify_succeeded.push_email_notification")
    @patch.object(target=BaseExporter, attribute="track_job")
    @patch.object(target=BaseExporter, attribute="send_export")
    @patch("exports.export_tasks.await_cohorts.time.sleep")
    @patch("exports.export_tasks.create_cohorts.cohort_service.create_cohort_subset")
    @patch("exports.export_tasks.notify_received.push_email_notification")
    def test_csv_export_with_failure_on_creating_cohort_subsets(self,
                                                                mock_push_reception_notif,
                                                                mock_create_cohort_subset,
                                                                mock_sleep,
                                                                mock_send_export,
                                                                mock_track_job,
                                                                mock_push_success_notif,
                                                                mock_push_failure_notif):
        mock_push_reception_notif.return_value = None
        mock_create_cohort_subset.return_value = self.cohort_subset
        mock_push_success_notif.return_value = None
        mock_send_export.return_value = "some-valid-job-id"
        mock_track_job.return_value = JobStatus.finished

        tables_data = [dict(table_name="person",
                            cohort_result_source=self.cohort.uuid,
                            fhir_filter=self.fhir_filter.uuid),
                       ]

        self.cohort_subset.request_job_status = JobStatus.failed
        self.cohort_subset.save()

        result = export_service.proceed_with_export(export=self.csv_export, tables=tables_data, auth_headers={})

        mock_push_reception_notif.assert_called_once()
        mock_create_cohort_subset.assert_called_once()
        mock_sleep.assert_called_once()
        mock_send_export.assert_not_called()
        mock_track_job.assert_not_called()
        mock_push_success_notif.assert_not_called()
        self.assertEqual(mock_push_failure_notif.call_count, 2) # notif for owner and for admins

        self.csv_export.refresh_from_db()
        self.assertTrue(self.csv_export.request_job_status == JobStatus.failed)
        self.assertIsNotNone(self.csv_export.request_job_fail_msg)

        self.assertTrue(result)


@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
class ExportServiceRetryTestCase(TestCase):
    def setUp(self):
        super().setUp()
        self.export_user, _ = new_user_and_profile()
        self.datalab = Datalab.objects.create(name="test_datalab",
                                              infrastructure_provider=InfrastructureProvider.objects.create(name="provider"))
        base_export_data = dict(owner=self.export_user,
                                motivation="motivation",
                                nominative=True,
                                target_name="some_target_name",
                                request_job_status=JobStatus.failed,
                                request_job_fail_msg="It failed")
        self.export = Export.objects.create(**base_export_data, output_format="csv")
        self.cohort = CohortResult.objects.create(name='cohort',
                                                  owner=self.export_user,
                                                  request_job_status=JobStatus.finished)
        self.export_table = ExportTable.objects.create(
            export=self.export,
            name="person",
            cohort_result_source=self.cohort
        )

    @patch("exports.services.export.chain")
    def test_retry_export_failed_at_api_side(self, mock_chain):
        # This export failed after being sent to the export API
        self.export.request_job_id = "some-api-job-id"
        self.export.save()

        export_service.retry(export=self.export, auth_headers={})

        self.export.refresh_from_db()
        self.assertEqual(self.export.request_job_status, JobStatus.new)
        self.assertEqual(self.export.request_job_fail_msg, "")
        self.assertTrue(self.export.retried)

        # Check that the correct task chain is created
        mock_chain.assert_called_once()
        # Get the arguments passed to chain()
        tasks = mock_chain.call_args[0]
        task_names = [t.task for t in tasks]

        self.assertNotIn(f"{relaunch_cohort_subsets.__module__}.{relaunch_cohort_subsets.__name__}", task_names)
        self.assertIn(f"{prepare_export.__module__}.{prepare_export.__name__}", task_names)
        self.assertIn(f"{send_export_request.__module__}.{send_export_request.__name__}", task_names)

    @patch("exports.services.export.chain")
    def test_retry_export_failed_before_api_call_with_failed_subsets(self, mock_chain):
        # This export failed before being sent to the export API
        self.assertIn(self.export.request_job_id, ['', None])

        # One of the cohort subsets has failed
        failed_subset = CohortResult.objects.create(
            name='failed subset',
            owner=self.export_user,
            request_job_status=JobStatus.failed,
            is_subset=True
        )
        self.export_table.cohort_result_subset = failed_subset
        self.export_table.save()

        export_service.retry(export=self.export, auth_headers={})

        self.export.refresh_from_db()
        self.assertEqual(self.export.request_job_status, JobStatus.new)

        # Check that the correct task chain is created
        mock_chain.assert_called_once()
        tasks = mock_chain.call_args[0]
        task_names = [t.task for t in tasks]

        self.assertIn(f"{relaunch_cohort_subsets.__module__}.{relaunch_cohort_subsets.__name__}", task_names)
        self.assertIn(f"{await_cohort_subsets.__module__}.{await_cohort_subsets.__name__}", task_names)
        self.assertIn(f"{prepare_export.__module__}.{prepare_export.__name__}", task_names)

    @patch("exports.services.export.chain")
    def test_retry_export_failed_before_api_call_without_failed_subsets(self, mock_chain):
        # This export failed before being sent to the export API
        self.assertIn(self.export.request_job_id, ['', None])

        # The cohort subset is finished
        finished_subset = CohortResult.objects.create(
            name='finished subset',
            owner=self.export_user,
            request_job_status=JobStatus.finished,
            is_subset=True
        )
        self.export_table.cohort_result_subset = finished_subset
        self.export_table.save()

        export_service.retry(export=self.export, auth_headers={})

        self.export.refresh_from_db()
        self.assertEqual(self.export.request_job_status, JobStatus.new)

        # Check that the correct task chain is created
        mock_chain.assert_called_once()
        tasks = mock_chain.call_args[0]
        task_names = [t.task for t in tasks]

        self.assertNotIn(f"{relaunch_cohort_subsets.__module__}.{relaunch_cohort_subsets.__name__}", task_names)
        self.assertNotIn(f"{await_cohort_subsets.__module__}.{await_cohort_subsets.__name__}", task_names)
        self.assertIn(f"{prepare_export.__module__}.{prepare_export.__name__}", task_names)

    @patch("exports.services.export.chain")
    def test_retry_export_restores_deleted_tables(self, mock_chain):
        # This export failed before being sent to the export API
        self.assertIn(self.export.request_job_id, ['', None])
        # Soft-delete a table
        self.export_table.delete()

        export_service.retry(export=self.export, auth_headers={})

        self.export_table.refresh_from_db()
        self.assertIsNone(self.export_table.deleted)
        mock_chain.assert_called_once()

