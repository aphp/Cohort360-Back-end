from django.core.cache import cache
from django.test import SimpleTestCase, override_settings

from exports.exceptions import DownloadTicketUnavailable, InvalidDownloadTicket
from exports.services.download_ticket import ExportDownloadTicketService


LOC_MEM_CACHE = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": "export-download-tickets"}}
DUMMY_CACHE = {"default": {"BACKEND": "admin_cohort.tools.cache.CustomDummyCache"}}


@override_settings(CACHES=LOC_MEM_CACHE, EXPORT_DOWNLOAD_TICKET_TTL_SECONDS=60)
class ExportDownloadTicketServiceTest(SimpleTestCase):
    def setUp(self):
        cache.clear()
        self.service = ExportDownloadTicketService()

    def test_ticket_is_bound_to_export_and_single_use(self):
        token = self.service.issue(export_uuid="export-1", user_id="user-1")

        payload = self.service.consume(token=token, expected_export_uuid="export-1")

        self.assertEqual(payload, {"export_uuid": "export-1", "user_id": "user-1"})
        with self.assertRaises(InvalidDownloadTicket):
            self.service.consume(token=token, expected_export_uuid="export-1")

    def test_ticket_cannot_be_used_for_another_export(self):
        token = self.service.issue(export_uuid="export-1", user_id="user-1")

        with self.assertRaises(InvalidDownloadTicket):
            self.service.consume(token=token, expected_export_uuid="export-2")

    @override_settings(CACHES=DUMMY_CACHE)
    def test_ticket_creation_fails_closed_without_shared_cache(self):
        with self.assertRaises(DownloadTicketUnavailable):
            self.service.issue(export_uuid="export-1", user_id="user-1")
