from enum import Enum


class ExportTypes(Enum):
    CSV = "csv"
    XLSX = "xlsx"
    HIVE = "hive"

    @staticmethod
    def default() -> str:
        return ExportTypes.CSV.value

    @property
    def allow_download(self) -> bool:
        return self in (ExportTypes.CSV,
                        ExportTypes.XLSX)

    @property
    def allow_to_clean(self) -> bool:
        return self in (ExportTypes.CSV,
                        ExportTypes.XLSX)
