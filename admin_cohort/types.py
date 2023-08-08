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
    def __init__(self, **kwargs):
        self.access = kwargs.get('access', kwargs.get('access_token'))
        self.refresh = kwargs.get('refresh', kwargs.get('refresh_token'))
        self.last_connection = kwargs.get('last_connection', {})


class UserInfo:

    def __init__(self, **kwargs):
        self.username = kwargs.get("username", kwargs.get("preferred_username"))
        self.firstname = kwargs.get("firstname", kwargs.get("given_name"))
        self.lastname = kwargs.get("lastname", kwargs.get("family_name"))
        self.email = kwargs.get("email", f"{self.firstname}.{self.lastname}@aphp.fr")

    @classmethod
    def solr(cls):
        return cls(username="SOLR_ETL",
                   firstname="Solr",
                   lastname="ETL",
                   email="solr.etl@aphp.fr")

    @classmethod
    def sjs(cls):
        return cls(username="SPARK_JOB_SERVER",
                   firstname="SparkJob",
                   lastname="SERVER",
                   email="spark.jobserver@aphp.fr")


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
