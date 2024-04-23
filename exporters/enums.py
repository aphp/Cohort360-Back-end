from enum import Enum


class ExportTypes(Enum):
    CSV = "csv"
    HIVE = "hive"

    @staticmethod
    def default() -> str:
        return ExportTypes.CSV.value

    @property
    def allow_download(self) -> bool:
        return self == ExportTypes.CSV

    @property
    def allow_to_clean(self) -> bool:
        return self == ExportTypes.CSV
