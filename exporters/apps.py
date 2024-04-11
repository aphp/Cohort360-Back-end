import os
from enum import Enum

from django.apps import AppConfig
from django.conf import settings


class ExportersConfig(AppConfig):
    name = 'exporters'

    def ready(self):
        env = os.environ
        settings.EXPORT_TYPES_CLASS = ExportTypes

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

        settings.EXPORT_API_CONF = {
            "API_URL": env.get('EXPORT_API_URL'),
            "API_VERSION": env.get('EXPORT_API_VERSION'),
            "TOKENS": env.get('EXPORT_API_TOKENS'),
            "EXPORT_ENVIRONMENT": env.get('EXPORT_ENVIRONMENT')
        }


class ExportTypes(Enum):
    CSV = "csv"
    HIVE = "hive"

    @property
    def allow_download(self) -> bool:
        return self == ExportTypes.CSV

    @property
    def allow_to_clean(self) -> bool:
        return self == ExportTypes.CSV
