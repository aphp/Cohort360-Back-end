import logging
import os
from datetime import timedelta

from django.http import StreamingHttpResponse
from django.utils import timezone
from requests import RequestException

from admin_cohort.settings import DAYS_TO_KEEP_EXPORTED_FILES
from admin_cohort.types import JobStatus
from exports.emails import push_email_notification, exported_csv_files_deleted
from exports.exceptions import BadRequestError, FilesNoLongerAvailable, StorageProviderException
from exports.exporters.csv_exporter import CSVExporter
from exports.enums import ExportType
from exports.exporters.hive_exporter import HiveExporter
from exports.models import ExportRequest, Export
from exports.services.storage_provider import HDFSStorageProvider


STORAGE_PROVIDERS = os.environ.get("STORAGE_PROVIDERS").split(',')

_logger = logging.getLogger('django.request')


class Exporter:

    def __init__(self):
        self.exporters = {ExportType.CSV.value: CSVExporter,
                          ExportType.HIVE.value: HiveExporter
                          }

    def handle_export(self, export_id: str, export_model: ExportRequest | Export) -> None:
        export = export_model.objects.get(pk=export_id)
        exporter = self.exporters[export.output_format]
        exporter().handle_export(export=export)


class ExportDownloader:

    def __init__(self):
        self.storage_provider = HDFSStorageProvider(servers_urls=STORAGE_PROVIDERS)

    def download(self, export: ExportRequest | Export):
        if not export.downloadable():
            raise BadRequestError("The export is not done yet or has failed or not of type CSV")
        if not export.available_for_download():
            raise FilesNoLongerAvailable("The exported files are no longer available on the server.")
        try:
            response = StreamingHttpResponse(streaming_content=self.stream_file(export.target_full_path))
            file_size = self.get_file_size(file_name=export.target_full_path)
            response['Content-Type'] = 'application/zip'
            response['Content-Length'] = file_size
            response['Content-Disposition'] = f"attachment; filename=export_{export.cohort_id}.zip"
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

    def delete_exported_files(self):
        d = timezone.now() - timedelta(days=DAYS_TO_KEEP_EXPORTED_FILES)
        export_requests = ExportRequest.objects.filter(request_job_status=JobStatus.finished,
                                                       output_format=ExportType.CSV,
                                                       is_user_notified=True,
                                                       insert_datetime__lte=d,
                                                       cleaned_at__isnull=True)
        for export_request in export_requests:
            try:
                self.storage_provider.delete_file(file_name=export_request.target_full_path)
            except (RequestException, StorageProviderException) as e:
                _logger.exception(f"ExportRequest {export_request.id}: {e}")

            notification_data = dict(recipient_name=export_request.owner.display_name,
                                     recipient_email=export_request.owner.email,
                                     cohort_id=export_request.cohort_id)
            push_email_notification(base_notification=exported_csv_files_deleted, **notification_data)
            export_request.cleaned_at = timezone.now()
            export_request.save()



