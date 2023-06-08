from enum import Enum
from typing import List


class LoginError(Exception):
    pass


class ServerError(Exception):
    pass


class WorkflowError(Exception):
    pass


class MissingDataError(Exception):
    pass


class PersonIdentity:
    def __init__(self, firstname, lastname, user_id, email):
        self.firstname = firstname
        self.lastname = lastname
        self.user_id = user_id
        self.email = email


class JwtTokens:
    def __init__(self, access: str, refresh: str, last_connection: dict = None, **kwargs):
        self.access = access
        self.refresh = refresh
        self.last_connection = last_connection if last_connection else {}


class UserInfo:
    def __init__(self, username: str, firstname: str, lastname: str, email: str = "", **kwargs):
        self.username = username
        self.firstname = firstname
        self.lastname = lastname
        self.email = email or f"{firstname}.{lastname}@aphp.fr"


class StrEnum(str, Enum):
    def __str__(self):
        return self.value

    @classmethod
    def list(cls, exclude: List[str] = None):
        exclude = exclude or [""]
        return [c.value for c in cls if c.value not in exclude]


class JobStatus(StrEnum):
    new = "new"
    denied = "denied"
    validated = "validated"
    pending = "pending"
    long_pending = "long_pending"
    started = "started"
    failed = "failed"
    cancelled = "cancelled"
    finished = "finished"
    cleaned = "cleaned"
    unknown = "unknown"
