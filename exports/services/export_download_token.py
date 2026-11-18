from dataclasses import dataclass

from django.conf import settings
from django.core import signing

from admin_cohort.models import User
from exports.models import Export

EXPORT_DOWNLOAD_TOKEN_SALT = "exports.export_download_token"


@dataclass(frozen=True)
class ExportDownloadToken:
    username: str
    export_uuid: str


def create_export_download_token(user: User, export: Export) -> str:
    signer = signing.TimestampSigner(salt=EXPORT_DOWNLOAD_TOKEN_SALT)
    return signer.sign_object({"user": user.pk, "export": str(export.uuid)})


def read_export_download_token(token: str) -> ExportDownloadToken:
    """Raises signing.BadSignature (or its subclass SignatureExpired) if the token is invalid or too old."""
    signer = signing.TimestampSigner(salt=EXPORT_DOWNLOAD_TOKEN_SALT)
    data = signer.unsign_object(token, max_age=settings.EXPORT_DOWNLOAD_TOKEN_MAX_AGE)
    return ExportDownloadToken(username=data["user"], export_uuid=data["export"])
