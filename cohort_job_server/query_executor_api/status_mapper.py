from admin_cohort.types import JobStatus


status_mapper = {"KILLED": JobStatus.cancelled,
                 "FINISHED": JobStatus.finished,
                 "RUNNING": JobStatus.started,
                 "STARTED": JobStatus.started,
                 "ERROR": JobStatus.failed,
                 "UNKNOWN": JobStatus.unknown,
                 "PENDING": JobStatus.pending,
                 "LONG_PENDING": JobStatus.long_pending
                 }


def query_executor_status_mapper(status: str) -> JobStatus:
    status = status and status.upper() or None
    return status_mapper.get(status)
