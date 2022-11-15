from admin_cohort.tools import StrEnum


class LoginError(Exception):
    pass


class ServerError(Exception):
    pass


class IdResp:
    def __init__(self, firstname, lastname, user_id, email, **kwargs):
        self.firstname = firstname
        self.lastname = lastname
        self.user_id = user_id
        self.email = email
        for k, v in kwargs.items():
            setattr(self, k, v)


class JwtTokens:
    def __init__(self, access: str, refresh: str, last_connection: dict = None, **kwargs):
        self.access = access
        self.refresh = refresh
        self.last_connection = last_connection if last_connection else {}


class UserInfo:
    def __init__(self, username: str, email: str, firstname: str, lastname: str, **kwargs):
        self.username = username
        self.email = email
        self.firstname = firstname
        self.lastname = lastname


class JobStatus(StrEnum):
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
