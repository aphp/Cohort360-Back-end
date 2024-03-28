import logging
import os

from django.http import StreamingHttpResponse

from exports.exceptions import BadRequestError, FilesNoLongerAvailable, StorageProviderException
from exports.models import ExportRequest, Export
from exports.services.storage_provider import HDFSStorageProvider

# todo: replace env var `DAYS_TO_DELETE_CSV_FILES`  by  `DAYS_TO_KEEP_EXPORTED_FILES`
#       add  new env var `STORAGE_PROVIDERS_URLS`
STORAGE_PROVIDERS_URLS = os.environ.get("STORAGE_PROVIDERS_URLS", "server1,server2").split(',')

_logger = logging.getLogger('django.request')


class ExportOperator:
    
    def __init__(self, *args, **kwargs):
        self.storage_provider = HDFSStorageProvider(servers_urls=STORAGE_PROVIDERS_URLS)


class ExportDownloader(ExportOperator):

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


class ExportCleaner(ExportOperator):

    def delete_file(self, file_name: str):
        self.storage_provider.delete_file(file_name=file_name)


