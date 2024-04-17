import os

from django.apps import AppConfig
from django.conf import settings

from exporters.enums import ExportTypes


# set EXPORT_TYPES_CLASS before Django loads models
settings.EXPORT_TYPES_CLASS = ExportTypes


class ExportersConfig(AppConfig):
    name = 'exporters'

    def ready(self):
        settings.EXPORTERS = [
            {
                "TYPE": ExportTypes.CSV.value,
                "EXPORTER_CLASS": "exporters.csv_exporter.CSVExporter"
            },
            {
                "TYPE": ExportTypes.HIVE.value,
                "EXPORTER_CLASS": "exporters.hive_exporter.HiveExporter"
            }
        ]
        env = os.environ
        settings.EXPORT_API_CONF = {
            "API_URL": env.get('EXPORT_API_URL'),
            "API_VERSION": env.get('EXPORT_API_VERSION'),
            "TOKENS": env.get('EXPORT_API_TOKENS'),
            "EXPORT_ENVIRONMENT": env.get('EXPORT_ENVIRONMENT')
        }
