from admin_cohort.tools import StrEnum


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

    @classmethod
    def oidc(cls, oidc_vals):
        return cls(username=oidc_vals.get('preferred_username'),
                   firstname=oidc_vals.get('given_name'),
                   lastname=oidc_vals.get('family_name'),
                   email=oidc_vals.get('email'))


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
