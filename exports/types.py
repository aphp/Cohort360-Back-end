from enum import Enum
from typing import List


class StrEnum(str, Enum):
    def __str__(self):
        return self.value

    @classmethod
    def list(cls, exclude: List[str] = None):
        exclude = exclude or [""]
        return [c.value for c in cls if c.value not in exclude]


class ExportType(StrEnum):
    CSV: str = "csv"
    HIVE: str = "hive"
    PSQL: str = "psql"


class NewJobStatus(StrEnum):
    new = "new"
    denied = "denied"
    validated = "validated"
    pending = "pending"
    started = "started"
    failed = "failed"
    cancelled = "cancelled"
    finished = "finished"
    cleaned = "cleaned"
    unknown = "unknown"


class JobStatus(StrEnum):
    KILLED = "killed"
    FINISHED = "finished"
    RUNNING = "running"
    STARTED = "started"
    ERROR = "error"
    UNKNOWN = "unknown"
    PENDING = "pending"


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
