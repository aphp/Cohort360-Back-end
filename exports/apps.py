from django.apps import AppConfig
from django.conf import settings


class ExportsConfig(AppConfig):
    name = 'exports'

    def ready(self):

        settings.EXPORTERS = getattr(settings, "EXPORTERS", [
            {
                "TYPE": "plain",
                "EXPORTER_CLASS": "exports.services.exporter_manager.DefaultExporter"
            }
        ])
