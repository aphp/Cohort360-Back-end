from admin_cohort.types import StrEnum, JobStatus


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
    SIZE_BYTES: str = "Size Bytes"


class ApiJobResponse:
    def __init__(self, status: JobStatus, output: str = "", err: str = ""):
        self.status: JobStatus = status
        self.output: str = output
        self.err: str = err

    @property
    def has_ended(self):
        return self.status in [JobStatus.failed, JobStatus.cancelled,
                               JobStatus.finished, JobStatus.unknown]


class HdfsServerUnreachableError(Exception):
    pass
