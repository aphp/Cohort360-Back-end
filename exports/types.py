from hdfs import HdfsError

from admin_cohort.types import StrEnum


class ExportType(StrEnum):
    CSV: str = "csv"
    HIVE: str = "hive"


class ExportStatus(StrEnum):
    PENDING: str = "pending"
    SENT_TO_DE: str = "sent_to_dataexporter"
    DELIVERED: str = "delivered"


class StatType(StrEnum):
    INT: str = "Integer"
    TXT: str = "Text"
    SIZE_BYTES: str = "SizeBytes"


class HdfsServerUnreachableError(HdfsError):
    pass
