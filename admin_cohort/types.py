from admin_cohort.tools import StrEnum


class UserInfo:
    def __init__(self, username: str, email: str,
                 firstname: str, lastname: str, **kwargs):
        self.username = username
        self.email = email
        self.firstname = firstname
        self.lastname = lastname


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
