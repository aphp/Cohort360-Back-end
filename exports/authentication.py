from django.core import signing
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from admin_cohort.models import User
from exports.services.export_download_token import read_export_download_token

EXPORT_DOWNLOAD_TOKEN_PARAM = "token"  # nosec B105


class ExportDownloadTokenAuthentication(BaseAuthentication):
    """Authenticates a browser download (`GET /exports/<uuid>/download/?token=...`), which can't send the Bearer."""

    def authenticate(self, request):
        token = request.query_params.get(EXPORT_DOWNLOAD_TOKEN_PARAM)
        if not token:
            return None
        try:
            export_download_token = read_export_download_token(token)
        except signing.BadSignature:
            raise AuthenticationFailed("Invalid or expired export download token")
        user = User.objects.filter(pk=export_download_token.username).first()
        if user is None:
            raise AuthenticationFailed("Invalid or expired export download token")
        return user, export_download_token
