import os

from django.apps import AppConfig
from exporters.enums import ExportTypes


class ExportersConfig(AppConfig):
    name = 'exporters'

    EXPORT_TYPES_CLASS = ExportTypes

    EXPORTERS = [
        {
            "TYPE": ExportTypes.CSV.value,
            "EXPORTER_CLASS": "exporters.exporters.csv_exporter.CSVExporter"
        },
        {
            "TYPE": ExportTypes.XLSX.value,
            "EXPORTER_CLASS": "exporters.exporters.xlsx_exporter.XLSXExporter"
        },
        {
            "TYPE": ExportTypes.HIVE.value,
            "EXPORTER_CLASS": "exporters.exporters.hive_exporter.HiveExporter"
        }
    ]

    env = os.environ
    THIRD_PARTY_API_CONF = {
        "INFRA_API": {
            "API_URL": env.get('INFRA_API_URL'),
            "AUTH_TOKEN": env.get('INFRA_HADOOP_TOKEN'),
            "TASK_STATUS_ENDPOINT": env.get('HADOOP_TASK_STATUS_ENDPOINT'),
            "CREATE_DB_ENDPOINT": env.get('CREATE_DB_ENDPOINT'),
            "ALTER_DB_ENDPOINT": env.get('ALTER_DB_ENDPOINT'),
        },
        "EXPORT_API": {
            "API_URL": env.get('EXPORT_API_URL'),
            "AUTH_TOKEN": env.get('EXPORT_AUTH_TOKEN'),
            "TASK_STATUS_ENDPOINT": env.get('EXPORT_TASK_STATUS_ENDPOINT'),
            "DISABLE_TERMINOLOGY": env.get('DISABLE_TERMINOLOGY', False),
        },
    }
