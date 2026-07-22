from datetime import timedelta
from unittest import mock
from unittest.mock import MagicMock, patch

from django.conf import settings
from django.utils import timezone
from rest_framework import status

from admin_cohort.types import JobStatus
from exports.apps import ExportsConfig
from exports.exceptions import BadRequestError, FilesNoLongerAvailable, InvalidRangeError
from exports.models import Export, ExportTable
from exports.services.export_operators import ExportDownloader
from exports.tests.test_view_export_request import ExportsTests


class TestExportDownloader(ExportsTests):
    def setUp(self):
        super().setUp()
        with mock.patch("exports.services.export_operators.HDFSStorageProvider"):
            self.export_downloader = ExportDownloader()
            self.mock_storage_provider = self.export_downloader.storage_provider

        downloadable_export_types = [t.value for t in ExportsConfig.ExportTypes if t.allow_download]

        self.export1 = Export.objects.create(
            owner=self.user1,
            output_format=downloadable_export_types and downloadable_export_types[0] or None,
            request_job_status=JobStatus.finished,
            target_location="target_location",
            is_user_notified=True,
            nominative=True,
        )
        ExportTable.objects.create(export=self.export1, name="Patient", cohort_result_source=self.user1_cohort)

    def test_successfully_download_export(self):
        self.mock_storage_provider.get_file_size.return_value = 11111
        with patch.object(self.export_downloader.storage_provider, "stream_file") as mock_stream_file:
            mock_file = MagicMock()
            mock_stream_file.return_value.__enter__.return_value = mock_file
            mock_file.__iter__.return_value = iter(["chunk1", "chunk2"])
            response = self.export_downloader.download(self.export1)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Length"], "11111")
        self.assertEqual(response["Accept-Ranges"], "bytes")
        self.assertEqual(response["X-Accel-Buffering"], "no")
        self.mock_storage_provider.get_file_size.assert_called_once()

    def test_download_export_byte_range(self):
        self.mock_storage_provider.get_file_size.return_value = 1000
        mock_file = MagicMock()
        mock_file.__iter__.return_value = iter([b"partial"])
        self.mock_storage_provider.stream_file.return_value.__enter__.return_value = mock_file

        response = self.export_downloader.download(self.export1, range_header="bytes=100-199")
        list(response.streaming_content)

        self.assertEqual(response.status_code, status.HTTP_206_PARTIAL_CONTENT)
        self.assertEqual(response["Content-Length"], "100")
        self.assertEqual(response["Content-Range"], "bytes 100-199/1000")
        self.mock_storage_provider.stream_file.assert_called_once_with(
            file_name=f"{self.export1.target_full_path}.zip", offset=100, length=100
        )

    def test_rejects_invalid_byte_range(self):
        self.mock_storage_provider.get_file_size.return_value = 1000

        with self.assertRaises(InvalidRangeError):
            self.export_downloader.download(self.export1, range_header="bytes=1000-")

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
