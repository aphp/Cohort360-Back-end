from datetime import timedelta
from unittest import mock
from unittest.mock import MagicMock, patch

from django.conf import settings
from django.utils import timezone
from rest_framework import status

from admin_cohort.types import JobStatus
from exports import ExportTypes
from exports.exceptions import BadRequestError, FilesNoLongerAvailable
from exports.models import Export, ExportTable
from exports.services.export_operators import ExportDownloader
from exports.tests.test_view_export_request import ExportsTests


class TestExportDownloader(ExportsTests):

    def setUp(self):
        super().setUp()
        with mock.patch("exports.services.export_operators.HDFSStorageProvider"):
            self.export_downloader = ExportDownloader()
            self.mock_storage_provider = self.export_downloader.storage_provider

        downloadable_export_types = [t.value for t in ExportTypes if t.allow_download]

        self.export1 = Export.objects.create(owner=self.user1,
                                             output_format=downloadable_export_types and downloadable_export_types[0] or None,
                                             request_job_status=JobStatus.finished,
                                             target_location="target_location",
                                             is_user_notified=True,
                                             nominative=True)
        ExportTable.objects.create(export=self.export1,
                                   name="person",
                                   cohort_result_source=self.user1_cohort)

    def test_successfully_download_export(self):
        self.mock_storage_provider.get_file_size.return_value = 11111
        with patch.object(self.export_downloader.storage_provider, 'stream_file') as mock_stream_file:
            mock_file = MagicMock()
            mock_stream_file.return_value.__enter__.return_value = mock_file
            mock_file.__iter__.return_value = iter(['chunk1', 'chunk2'])
            response = self.export_downloader.download(self.export1)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.mock_storage_provider.get_file_size.assert_called_once()

    def test_error_download_export_type_plain(self):
        self.export1.output_format = "bad_format"
        with self.assertRaises(BadRequestError):
            self.export_downloader.download(self.export1)

    def test_error_download_export_not_finished(self):
        self.export1.request_job_status = JobStatus.pending.value
        with self.assertRaises(BadRequestError):
            self.export_downloader.download(self.export1)

    def test_error_download_old_export(self):
        self.export1.created_at = (timezone.now() - timedelta(days=settings.DAYS_TO_KEEP_EXPORTED_FILES + 1))
        self.export1.save()
        with self.assertRaises(FilesNoLongerAvailable):
            self.export_downloader.download(self.export1)
