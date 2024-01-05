from hdfs import HdfsError

from admin_cohort.types import StrEnum


class ExportType(StrEnum):
    CSV: str = "csv"
    HIVE: str = "hive"


class ExportStatus(StrEnum):
    PENDING: str = "En attente"
    SENT_TO_DE: str = "Envoyé au DataExporter"
    DELIVERED: str = "Livré"


class StatType(StrEnum):
    INT: str = "Integer"
    TXT: str = "Text"
    SIZE_BYTES: str = "SizeBytes"


class HdfsServerUnreachableError(HdfsError):
    pass
