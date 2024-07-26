from dataclasses import dataclass
from enum import Enum
from typing import List


class LoginError(Exception):
    pass


class ServerError(Exception):
    pass


class MissingDataError(Exception):
    pass


class PersonIdentity:
    def __init__(self, firstname, lastname, username, email):
        self.firstname = firstname
        self.lastname = lastname
        self.username = username
        self.email = email


@dataclass
class AuthTokens:
    access_token: str
    refresh_token: str


class OIDCAuthTokens(AuthTokens):

    def __init__(self, access_token: str, refresh_token: str, **kwargs):
        super().__init__(access_token, refresh_token)


class JWTAuthTokens(AuthTokens):
    def __init__(self, access: str, refresh: str, **kwargs):
        super().__init__(access_token=access, refresh_token=refresh)


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

    @property
    def is_end_state(self):
        return self in [JobStatus.failed,
                        JobStatus.cancelled,
                        JobStatus.finished,
                        JobStatus.unknown]
