from django.conf import settings
from exports.enums import DefaultExportTypes


if "exporters" in settings.INCLUDED_APPS:
    from exporters.apps import ExportersConfig
    ExportTypes = ExportersConfig.EXPORT_TYPES_CLASS
else:
    ExportTypes = DefaultExportTypes
