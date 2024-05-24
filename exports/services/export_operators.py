import logging
import os
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.http import StreamingHttpResponse
from django.utils import timezone
from django.utils.module_loading import import_string
from requests import RequestException

from admin_cohort.types import JobStatus
from exports import ExportTypes
from exports.emails import push_email_notification, exported_files_deleted
from exports.exceptions import BadRequestError, FilesNoLongerAvailable, StorageProviderException
from exports.models import Export
from exports.services.storage_provider import HDFSStorageProvider


STORAGE_PROVIDERS = os.environ.get("STORAGE_PROVIDERS").split(',')

_logger = logging.getLogger('django.request')


def load_available_exporters() -> dict:
    exporters = {}
    for exporter_conf in settings.EXPORTERS:
        try:
            export_type, cls_path = exporter_conf["TYPE"], exporter_conf["EXPORTER_CLASS"]
            export_type = ExportTypes(export_type).value
        except KeyError:
            raise ImproperlyConfigured("Missing `TYPE` or `EXPORTER_CLASS` key in exporter configuration")
        except ValueError as e:
            raise ImproperlyConfigured(f"Invalid export type: {e}")
        exporter = import_string(cls_path)
        if exporter:
            exporters[export_type] = exporter
        else:
            _logger.warning(f"Improperly configured exporter `{cls_path}`")
    if not exporters:
        raise ImproperlyConfigured("No exporter is configured")
    return exporters


class ExportManager:

    def __init__(self):
        self.exporters = load_available_exporters()

    def _get_exporter(self, export_type: str):
        try:
            return self.exporters[export_type]
        except KeyError:
            raise ImproperlyConfigured(f"Missing exporter configuration for type `{export_type}`")

    def validate(self, export_data: dict, **kwargs) -> None:
        exporter = self._get_exporter(export_data.get("output_format"))
        exporter().validate(export_data=export_data, **kwargs)

    def handle_export(self, export_id: str | int) -> None:
        try:
            export = Export.objects.get(pk=export_id)
        except Export.DoesNotExist:
            raise ValueError(f'No export matches the given ID : {export_id}')
        exporter = self._get_exporter(export.output_format)
        exporter().handle_export(export=export)

    def mark_as_failed(self, export: Export, reason: str) -> None:
        exporter = self._get_exporter(export.output_format)
        exporter().mark_export_as_failed(export=export, reason=reason)


class DefaultExporter:

    def validate(self, export_data: dict, **kwargs):
        raise NotImplementedError("Missing exporter implementation")

    def handle_export(self, export: Export):
        raise NotImplementedError("Missing exporter implementation")

    def mark_export_as_failed(self, export: Export, reason: str) -> None:
        export.request_job_status = JobStatus.failed
        export.request_job_fail_msg = reason
        export.save()


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
            file_name = f"export_{export.motivation}.zip"
            response['Content-Type'] = 'application/zip'
            response['Content-Length'] = file_size
            response['Content-Disposition'] = f"attachment; filename={file_name}"
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

            notification_data = dict(recipient_name=export.owner.display_name,
                                     recipient_email=export.owner.email,
                                     cohort_id=export.export_tables.first().cohort_result_source.fhir_group_id)
            push_email_notification(base_notification=exported_files_deleted, **notification_data)
            export.clean_datetime = timezone.now()
            export.save()



