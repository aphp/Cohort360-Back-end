import logging
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.http import StreamingHttpResponse
from django.utils import timezone
from django.utils.module_loading import import_string
from requests import RequestException

from admin_cohort.types import JobStatus
from exports.apps import ExportsConfig
from exports.emails import push_email_notification, exported_files_deleted
from exports.exceptions import BadRequestError, FilesNoLongerAvailable, StorageProviderException
from exports.models import Export
from exports.services.storage_provider import StorageProvider, get_storage_provider, storage_scheme


logger = logging.getLogger(__name__)

ExportTypes = ExportsConfig.ExportTypes
EXPORTERS = ExportsConfig.EXPORTERS


def load_available_exporters() -> dict:
    exporters = {}
    for exporter_conf in EXPORTERS:
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
            logger.warning(f"Improperly configured exporter `{cls_path}`")
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
        fmt = export_data.get("output_format")
        if not isinstance(fmt, str) or not fmt:
            raise ImproperlyConfigured("output_format is required")
        exporter = self._get_exporter(fmt)
        exporter().validate(export_data=export_data, **kwargs)

    def handle_export(self, export_id: str) -> None:
        try:
            export = Export.objects.get(pk=export_id)
        except Export.DoesNotExist:
            raise ValueError(f"No export matches the given ID : {export_id}")
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

    @staticmethod
    def mark_export_as_failed(export: Export, reason: str) -> None:
        export.request_job_status = JobStatus.failed
        export.request_job_fail_msg = reason
        export.save()


class ExportDownloader:
    def __init__(self):
        self.downloadable_export_types = [t.value for t in ExportTypes if t.allow_download]

    def download(self, export: Export) -> StreamingHttpResponse:
        if export.request_job_status != JobStatus.finished.value or export.output_format not in self.downloadable_export_types:
            raise BadRequestError("The export is not done yet or has failed or not downloadable")
        if not export.available_for_download():
            raise FilesNoLongerAvailable("The exported files are no longer available on the server.")
        file_path = f"{export.target_full_path}.zip"
        try:
            storage_provider = get_storage_provider(file_path)
            response = StreamingHttpResponse(streaming_content=self.stream_file(storage_provider, file_path))
            file_size = storage_provider.get_file_size(file_name=file_path)
            first = export.export_tables.first()
            if first is None or first.cohort_result_source is None:
                raise BadRequestError("Export has no table with cohort result source")
            download_file_name = f"export_{first.cohort_result_source.group_id}.zip"
            response["Content-Type"] = "application/zip"
            response["Content-Length"] = file_size
            response["Content-Disposition"] = f"attachment; filename={download_file_name}"
            return response
        except StorageProviderException as e:
            logger.exception(f"Export {export.pk}: error on `{storage_scheme(file_path)}` storage provider - {e}")
            raise e

    @staticmethod
    def stream_file(storage_provider: StorageProvider, file_name: str):
        try:
            with storage_provider.stream_file(file_name=file_name) as f:
                for chunk in f:
                    yield chunk
        except StorageProviderException:
            logger.exception(f"Error while streaming `{file_name}` from storage provider")
            raise


class ExportCleaner:
    def __init__(self):
        self.target_types = [t.value for t in ExportTypes if t.allow_to_clean]

    def delete_exported_files(self):
        d = timezone.now() - timedelta(days=settings.DAYS_TO_KEEP_EXPORTED_FILES)
        exports = Export.objects.filter(
            request_job_status=JobStatus.finished,
            output_format__in=self.target_types,
            is_user_notified=True,
            created_at__lte=d,
            clean_datetime__isnull=True,
        )
        providers: dict[str, StorageProvider] = {}
        for export in exports:
            file_path = f"{export.target_full_path}.zip"
            scheme = storage_scheme(file_path)
            try:
                provider = providers.get(scheme) or get_storage_provider(file_path)
                providers[scheme] = provider
                provider.delete_file(file_name=file_path)
            except (RequestException, StorageProviderException) as e:
                logger.exception(f"Export {export.pk}: {e}")
                return

            notification_data = {
                "recipient_name": export.owner.display_name,
                "recipient_email": export.owner.email,
                "cohort_id": export.export_tables.first().cohort_result_source.group_id,
            }
            push_email_notification(base_notification=exported_files_deleted, **notification_data)
            export.clean_datetime = timezone.now()
            export.save()
