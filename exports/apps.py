from enum import Enum

from django.apps import AppConfig
from django.conf import settings
from exports.enums import DefaultExportTypes


class ExportsConfig(AppConfig):
    name = "exports"

    if "exporters" in settings.INSTALLED_APPS:
        from exporters.apps import ExportersConfig

        ExportTypes: type[Enum] = ExportersConfig.EXPORT_TYPES_CLASS
        EXPORTERS = ExportersConfig.EXPORTERS
    else:
        ExportTypes = DefaultExportTypes
        EXPORTERS = [{"TYPE": "plain", "EXPORTER_CLASS": "exports.services.export_operators.DefaultExporter"}]
