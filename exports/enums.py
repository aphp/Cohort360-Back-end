from enum import Enum


class ExportType(Enum):
    CSV = "csv"
    HIVE = "hive"


class ExportStatus(Enum):
    PENDING: str = "pending"
    SENT_TO_DE: str = "sent_to_dataexporter"
    DELIVERED: str = "delivered"


class StatType(Enum):
    INT: str = "Integer"
    TXT: str = "Text"
    SIZE_BYTES: str = "SizeBytes"
