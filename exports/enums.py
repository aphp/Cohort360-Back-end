from enum import Enum


class DefaultExportTypes(Enum):
    PLAIN = "plain"

    @staticmethod
    def default() -> str:
        return DefaultExportTypes.PLAIN.value

    @property
    def allow_download(self) -> bool:
        return True

    @property
    def allow_to_clean(self) -> bool:
        return True


class ExportStatus(Enum):
    PENDING: str = "pending"
    SENT_TO_DE: str = "sent_to_dataexporter"
    DELIVERED: str = "delivered"


class StatType(Enum):
    INT: str = "Integer"
    TXT: str = "Text"
    SIZE_BYTES: str = "SizeBytes"
