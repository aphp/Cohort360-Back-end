from datetime import timedelta
from unittest import mock
from unittest.mock import MagicMock

from django.conf import settings
from django.utils import timezone
from rest_framework import status

from admin_cohort.types import JobStatus
from exports.apps import ExportsConfig
from exports.exceptions import BadRequestError, FilesNoLongerAvailable
from exports.models import Export, ExportTable
from exports.services.export_operators import ExportDownloader
from exports.tests.test_view_export_request import ExportsTests


class TestExportDownloader(ExportsTests):
    def setUp(self):
        super().setUp()
        self.export_downloader = ExportDownloader()
        self.mock_storage_provider = MagicMock()
        patcher = mock.patch(
            "exports.services.export_operators.get_storage_provider",
            return_value=self.mock_storage_provider,
        )
        self.mock_get_storage_provider = patcher.start()
        self.addCleanup(patcher.stop)

        downloadable_export_types = [t.value for t in ExportsConfig.ExportTypes if t.allow_download]

        self.export1 = Export.objects.create(
            owner=self.user1,
            output_format=downloadable_export_types and downloadable_export_types[0] or None,
            request_job_status=JobStatus.finished,
            target_location="target_location",
            target_name="target_name",
            is_user_notified=True,
            nominative=True,
        )
        ExportTable.objects.create(export=self.export1, name="Patient", cohort_result_source=self.user1_cohort)

    def _mock_stream_chunks(self, *chunks):
        mock_file = MagicMock()
        mock_file.__iter__.return_value = iter(chunks)
        self.mock_storage_provider.stream_file.return_value.__enter__.return_value = mock_file

    def test_successfully_download_export(self):
        self.mock_storage_provider.get_file_size.return_value = 11111
        self._mock_stream_chunks("chunk1", "chunk2")
        response = self.export_downloader.download(self.export1)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.mock_get_storage_provider.assert_called_once_with("target_location/target_name.zip")
        self.mock_storage_provider.get_file_size.assert_called_once()

    def test_successfully_download_export_from_s3(self):
        self.export1.target_location = "s3a://bucket/exports"
        self.export1.save()
        self.mock_storage_provider.get_file_size.return_value = 11111
        self._mock_stream_chunks("chunk1", "chunk2")
        response = self.export_downloader.download(self.export1)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.mock_get_storage_provider.assert_called_once_with("s3a://bucket/exports/target_name.zip")

    def test_error_download_export_type_plain(self):
        self.export1.output_format = "bad_format"
        with self.assertRaises(BadRequestError):
            self.export_downloader.download(self.export1)

    def test_error_download_export_not_finished(self):
        self.export1.request_job_status = JobStatus.pending.value
        with self.assertRaises(BadRequestError):
            self.export_downloader.download(self.export1)

    def test_error_download_old_export(self):
        self.export1.created_at = timezone.now() - timedelta(days=settings.DAYS_TO_KEEP_EXPORTED_FILES + 1)
        self.export1.save()
        with self.assertRaises(FilesNoLongerAvailable):
            self.export_downloader.download(self.export1)
