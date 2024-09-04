from django.apps import AppConfig
from django.conf import settings


class ExportsConfig(AppConfig):
    name = 'exports'

    if "exporters" in settings.INCLUDED_APPS:
        from exporters.apps import ExportersConfig
        EXPORTERS = ExportersConfig.EXPORTERS
    else:
        EXPORTERS = [
            {
                "TYPE": "plain",
                "EXPORTER_CLASS": "exports.services.export_operators.DefaultExporter"
            }
        ]
