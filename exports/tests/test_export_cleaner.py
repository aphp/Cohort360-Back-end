from datetime import timedelta
from unittest import mock
from unittest.mock import MagicMock

from django.conf import settings
from django.utils import timezone
from requests import RequestException

from admin_cohort.types import JobStatus
from exports.apps import ExportsConfig
from exports.models import Export, ExportTable
from exports.services.export_operators import ExportCleaner
from exports.tests.test_view_export_request import ExportsTests


class TestExportCleaner(ExportsTests):
    def setUp(self):
        super().setUp()
        self.export_cleaner = ExportCleaner()
        self.mock_storage_provider = MagicMock()
        patcher = mock.patch(
            "exports.services.export_operators.get_storage_provider",
            return_value=self.mock_storage_provider,
        )
        self.mock_get_storage_provider = patcher.start()
        self.addCleanup(patcher.stop)

        cleanable_export_types = [t.value for t in ExportsConfig.ExportTypes if t.allow_to_clean]

        self.export1 = Export.objects.create(
            owner=self.user1,
            output_format=cleanable_export_types and cleanable_export_types[0] or None,
            request_job_status=JobStatus.finished,
            target_location="target_location",
            target_name="target_name",
            is_user_notified=True,
            nominative=True,
        )
        self.export_table = ExportTable.objects.create(export=self.export1, name="table01", cohort_result_source=self.user1_cohort)

    def update_export_insert_datetime(self) -> None:
        self.export1.created_at = timezone.now() - timedelta(days=settings.DAYS_TO_KEEP_EXPORTED_FILES)
        self.export1.save()

    @mock.patch("exports.services.export_operators.push_email_notification")
    def test_delete_exported_files(self, mock_push_notification: MagicMock):
        self.mock_storage_provider.delete_file.return_value = None
        mock_push_notification.return_value = None
        self.update_export_insert_datetime()
        self.export_cleaner.delete_exported_files()
        self.mock_get_storage_provider.assert_called_once_with("target_location/target_name.zip")
        self.mock_storage_provider.delete_file.assert_called_once_with(file_name="target_location/target_name.zip")
        mock_push_notification.assert_called_once()
        self.export1.refresh_from_db()
        self.assertIsNotNone(self.export1.clean_datetime)

    @mock.patch("exports.services.export_operators.push_email_notification")
    def test_delete_exported_files_on_s3(self, mock_push_notification: MagicMock):
        self.export1.target_location = "s3a://bucket/exports"
        self.export1.save()
        self.mock_storage_provider.delete_file.return_value = None
        mock_push_notification.return_value = None
        self.update_export_insert_datetime()
        self.export_cleaner.delete_exported_files()
        self.mock_get_storage_provider.assert_called_once_with("s3a://bucket/exports/target_name.zip")
        self.mock_storage_provider.delete_file.assert_called_once_with(file_name="s3a://bucket/exports/target_name.zip")

    @mock.patch("exports.services.export_operators.push_email_notification")
    def test_error_delete_exported_files(self, mock_push_notification: MagicMock):
        self.mock_storage_provider.delete_file.side_effect = RequestException()
        self.update_export_insert_datetime()
        self.export_cleaner.delete_exported_files()
        self.mock_storage_provider.delete_file.assert_called_once()
        mock_push_notification.assert_not_called()
        self.export1.refresh_from_db()
        self.assertIsNone(self.export1.clean_datetime)
