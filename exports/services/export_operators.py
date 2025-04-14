import logging
import os
from datetime import timedelta

from django.conf import settings
from django.http import StreamingHttpResponse
from django.utils import timezone
from requests import RequestException

from admin_cohort.types import JobStatus
from exports.apps import ExportsConfig
from exports.emails import push_email_notification, exported_files_deleted
from exports.exceptions import BadRequestError, FilesNoLongerAvailable, StorageProviderException
from exports.models import Export
from exports.services.storage_provider import HDFSStorageProvider


_logger = logging.getLogger('django.request')

STORAGE_PROVIDERS = os.environ.get("STORAGE_PROVIDERS", "").split(',')
if not STORAGE_PROVIDERS:
    _logger.warning("No storage provider is configured!")

ExportTypes = ExportsConfig.ExportTypes


class DefaultExporter:

    def validate(self, export_data: dict, **kwargs):
        raise NotImplementedError("Missing exporter implementation")

    def handle_export(self, export: Export):
        raise NotImplementedError("Missing exporter implementation")


class ExportDownloader:

    def __init__(self):
        self.storage_provider = HDFSStorageProvider(servers_urls=STORAGE_PROVIDERS)
        self.downloadable_export_types = [t.value for t in ExportTypes if t.allow_download]

    def download(self, export: Export) -> StreamingHttpResponse:
        if export.request_job_status != JobStatus.finished.value \
           or export.output_format not in self.downloadable_export_types:
            raise BadRequestError("The export is not done yet or has failed or not downloadable")
        if not export.available_for_download():
            raise FilesNoLongerAvailable("The exported files are no longer available on the server.")
        try:
            file_path = f"{export.target_full_path}.zip"
            response = StreamingHttpResponse(streaming_content=self.stream_file(file_path))
            file_size = self.get_file_size(file_name=file_path)
            download_file_name = f"export_{export.export_tables.first().cohort_result_source.group_id}.zip"
            response["Content-Type"] = "application/zip"
            response["Content-Length"] = file_size
            response["Content-Disposition"] = f"attachment; filename={download_file_name}"
            return response
        except StorageProviderException as e:
            _logger.exception(f"Error occurred on Storage Provider `{self.storage_provider.name}` - {e}")
            raise e

    def stream_file(self, file_name: str):
        with self.storage_provider.stream_file(file_name=file_name) as f:
            for chunk in f:
                yield chunk

    def get_file_size(self, file_name: str) -> int:
        return self.storage_provider.get_file_size(file_name=file_name)


class ExportCleaner:

    def __init__(self):
        self.storage_provider = HDFSStorageProvider(servers_urls=STORAGE_PROVIDERS)
        self.target_types = [t.value for t in ExportTypes if t.allow_to_clean]

    def delete_exported_files(self):
        d = timezone.now() - timedelta(days=settings.DAYS_TO_KEEP_EXPORTED_FILES)
        exports = Export.objects.filter(request_job_status=JobStatus.finished,
                                        output_format__in=self.target_types,
                                        is_user_notified=True,
                                        created_at__lte=d,
                                        clean_datetime__isnull=True)
        for export in exports:
            try:
                self.storage_provider.delete_file(file_name=f"{export.target_full_path}.zip")
            except (RequestException, StorageProviderException) as e:
                _logger.exception(f"Export {export.pk}: {e}")
                return

            notification_data = {"recipient_name": export.owner.display_name,
                                 "recipient_email": export.owner.email,
                                 "cohort_id": export.export_tables.first().cohort_result_source.group_id
                                 }
            push_email_notification(base_notification=exported_files_deleted, **notification_data)
            export.clean_datetime = timezone.now()
            export.save()
