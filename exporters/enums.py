from enum import Enum, StrEnum

from admin_cohort.types import JobStatus


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
        return self.allow_download


class APIJobType(StrEnum):
    EXPORT = "export"
    HIVE_DB_CREATE = "hive_db_create"


class APIJobStatus(StrEnum):
    Received = 'Received'
    Running = 'Running'
    Pending = 'Pending'
    NotFound = 'NotFound'
    Revoked = 'Revoked'
    Retry = 'Retry'
    Failure = 'Failure'
    FinishedSuccessfully = 'FinishedSuccessfully'
    FinishedWithError = 'FinishedWithError'
    FinishedWithTimeout = 'FinishedWithTimeout'
    flowerNotAccessible = 'flowerNotAccessible'


status_mapper = {APIJobStatus.Received.value: JobStatus.new,
                 APIJobStatus.Pending.value: JobStatus.pending,
                 APIJobStatus.Retry.value: JobStatus.pending,
                 APIJobStatus.Running.value: JobStatus.started,
                 APIJobStatus.FinishedSuccessfully.value: JobStatus.finished,
                 APIJobStatus.FinishedWithError.value: JobStatus.failed,
                 APIJobStatus.FinishedWithTimeout.value: JobStatus.failed,
                 APIJobStatus.flowerNotAccessible.value: JobStatus.failed,
                 APIJobStatus.Failure.value: JobStatus.failed,
                 APIJobStatus.NotFound.value: JobStatus.failed,
                 APIJobStatus.Revoked.value: JobStatus.cancelled
                 }
