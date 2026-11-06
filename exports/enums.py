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


class StatType(str, Enum):
    INT = "Integer"
    TXT = "Text"
    SIZE_BYTES = "SizeBytes"


class ExportPurpose(str, Enum):
    CARE_SUPPORT = "care_support"
    ACTIVITY_MANAGEMENT = "activity_management"
    INTERNAL_RESEARCH = "internal_research"
    MULTICENTER_RESEARCH = "multicenter_research"
