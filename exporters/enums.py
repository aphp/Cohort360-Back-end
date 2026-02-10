from enum import StrEnum

from admin_cohort.types import JobStatus


class ExportTypes(StrEnum):
    CSV = "csv"
    XLSX = "xlsx"
    HIVE = "hive"

    @staticmethod
    def default() -> str:
        return ExportTypes.CSV

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


status_mapper = {APIJobStatus.Received: JobStatus.new,
                 APIJobStatus.Pending: JobStatus.pending,
                 APIJobStatus.Retry: JobStatus.pending,
                 APIJobStatus.Running: JobStatus.started,
                 APIJobStatus.FinishedSuccessfully: JobStatus.finished,
                 APIJobStatus.FinishedWithError: JobStatus.failed,
                 APIJobStatus.FinishedWithTimeout: JobStatus.failed,
                 APIJobStatus.flowerNotAccessible: JobStatus.failed,
                 APIJobStatus.Failure: JobStatus.failed,
                 APIJobStatus.NotFound: JobStatus.failed,
                 APIJobStatus.Revoked: JobStatus.cancelled
                 }
