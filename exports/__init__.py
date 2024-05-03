from django.conf import settings
from exports.enums import DefaultExportTypes

default_app_config = 'exports.apps.ExportsConfig'

ExportTypes = getattr(settings, "EXPORT_TYPES_CLASS", DefaultExportTypes)
