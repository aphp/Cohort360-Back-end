import logging

from django.conf import settings
from django.utils.module_loading import import_string

_logger = logging.getLogger('info')


def load_export_api(path: str):
    export_api = import_string(path)
    if not export_api:
        from exports.export_api.dummy_api import DummyAPI
        _logger.warning("No Default Export API is defined. Ensure the `DEFAULT_EXPORTS_API` setting is set")
        return DummyAPI
    return export_api


ExportAPI = load_export_api(path=settings.EXPORT_API_CONF.get("API_CLASS"))
