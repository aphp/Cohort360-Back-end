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
                "TYPE": ExportTypes.XLSX.value,
                "EXPORTER_CLASS": "exporters.csv_exporter.XLSXExporter"
            },
            {
                "TYPE": ExportTypes.HIVE.value,
                "EXPORTER_CLASS": "exporters.hive_exporter.HiveExporter"
            }
        ]
        env = os.environ
        settings.EXPORT_API_CONF = {
            "API_URL": env.get('EXPORT_API_URL'),
            "CSV_EXPORT_ENDPOINT": env.get('CSV_EXPORT_ENDPOINT'),
            "HIVE_EXPORT_ENDPOINT": env.get('HIVE_EXPORT_ENDPOINT'),
            "EXPORT_TASK_STATUS_ENDPOINT": env.get('EXPORT_TASK_STATUS_ENDPOINT'),
            "HADOOP_TASK_STATUS_ENDPOINT": env.get('HADOOP_TASK_STATUS_ENDPOINT'),
            "CREATE_DB_ENDPOINT": env.get('CREATE_DB_ENDPOINT'),
            "ALTER_DB_ENDPOINT": env.get('ALTER_DB_ENDPOINT'),
            "BIGDATA_TOKEN": env.get('INFRA_EXPORT_TOKEN'),
            "HADOOP_TOKEN": env.get('INFRA_HADOOP_TOKEN'),
            "EXPORT_ENVIRONMENT": env.get('EXPORT_ENVIRONMENT')
        }
