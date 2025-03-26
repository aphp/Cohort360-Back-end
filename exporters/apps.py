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
        "HADOOP_API": {
            "API_URL": env.get('HADOOP_API_URL'),
            "AUTH_TOKEN": env.get('INFRA_HADOOP_TOKEN'),
            "HIVE_DB_PATH": env.get('HIVE_DB_PATH'),
            "HIVE_USER": env.get('HIVE_USER'),
            "TASK_STATUS_ENDPOINT": "/hadoop/task_status",
            "CREATE_DB_ENDPOINT": "/hadoop/hive/create_base_hive",
            "ALTER_DB_ENDPOINT": "/hadoop/hdfs/chown_directory",
        },
        "EXPORT_API": {
            "API_URL": env.get('EXPORT_API_URL'),
            "AUTH_TOKEN": env.get('EXPORT_AUTH_TOKEN'),
            "EXPORT_CSV_PATH": env.get('EXPORT_CSV_PATH'),
            "EXPORT_XLSX_PATH": env.get('EXPORT_XLSX_PATH'),
            "DISABLE_DATA_TRANSLATION": env.get('DISABLE_DATA_TRANSLATION', False),
            "TASK_STATUS_ENDPOINT": "/api/task_status",
        },
    }
