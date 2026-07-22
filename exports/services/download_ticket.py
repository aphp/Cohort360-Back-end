import hashlib
import secrets

from django.conf import settings
from django.core.cache import cache

from exports.exceptions import DownloadTicketUnavailable, InvalidDownloadTicket


class ExportDownloadTicketService:
    cache_prefix = "export-download-ticket"
    cookie_prefix = "export_download_ticket_"

    @property
    def ttl_seconds(self) -> int:
        return settings.EXPORT_DOWNLOAD_TICKET_TTL_SECONDS

    @staticmethod
    def cookie_name(export_uuid) -> str:
        return f"{ExportDownloadTicketService.cookie_prefix}{str(export_uuid).replace('-', '')}"

    def issue(self, export_uuid, user_id) -> str:
        token = secrets.token_urlsafe(32)
        key = self._ticket_key(token)
        payload = {"export_uuid": str(export_uuid), "user_id": str(user_id)}
        cache.set(key, payload, timeout=self.ttl_seconds)
        if cache.get(key) != payload:
            raise DownloadTicketUnavailable("The shared download ticket cache is unavailable")
        return token

    def consume(self, token: str, expected_export_uuid) -> dict:
        key = self._ticket_key(token)
        payload = cache.get(key)
        if payload is None or payload.get("export_uuid") != str(expected_export_uuid):
            raise InvalidDownloadTicket("The download ticket is invalid or expired")

        claimed_key = f"{key}:claimed"
        if not cache.add(claimed_key, True, timeout=self.ttl_seconds):
            raise InvalidDownloadTicket("The download ticket has already been used")
        cache.delete(key)
        return payload

    def _ticket_key(self, token: str) -> str:
        digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
        return f"{self.cache_prefix}:{digest}"


export_download_ticket_service = ExportDownloadTicketService()
