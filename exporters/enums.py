from enum import Enum


class ExportTypes(Enum):
    CSV = "csv"
    HIVE = "hive"

    @property
    def allow_download(self) -> bool:
        return self == ExportTypes.CSV

    @property
    def allow_to_clean(self) -> bool:
        return self == ExportTypes.CSV
