from admin_cohort.types import StrEnum, NewJobStatus


class ExportType(StrEnum):
    CSV: str = "csv"
    HIVE: str = "hive"
    PSQL: str = "psql"


class ApiJobResponse:
    def __init__(self, status: NewJobStatus, output: str = "", err: str = ""):
        self.status: NewJobStatus = status
        self.output: str = output
        self.err: str = err

    @property
    def has_ended(self):
        return self.status in [NewJobStatus.failed, NewJobStatus.cancelled,
                               NewJobStatus.finished, NewJobStatus.unknown]


class HdfsServerUnreachableError(Exception):
    pass
