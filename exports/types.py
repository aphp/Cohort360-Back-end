from admin_cohort.types import StrEnum, JobStatus


class ExportType(StrEnum):
    CSV: str = "csv"
    HIVE: str = "hive"
    PSQL: str = "psql"


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
