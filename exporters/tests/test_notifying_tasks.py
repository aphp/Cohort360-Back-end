from unittest import mock
from unittest.mock import MagicMock

from exporters.notifications import (csv_export_received, csv_export_succeeded, hive_export_received, hive_export_succeeded,
                                     export_failed_notif_for_owner, export_failed_notif_for_admins)

from exporters.tests.base_test import ExportersTestBase
from exports.export_tasks import notify_export_received, notify_export_succeeded, mark_export_as_failed


class TestNotifyingTasks(ExportersTestBase):

    def setUp(self) -> None:
        super().setUp()

    @mock.patch("exports.export_tasks.notify_received.push_email_notification")
    def test_notify_csv_export_received(self, mock_push_notif):
        mock_push_notif.return_value = None
        notify_export_received(export_id=self.csv_export.pk, cohort_id="", cohort_name="")
        mock_push_notif.assert_called()
        self.assertEqual(mock_push_notif.call_args.kwargs["base_notification"],
                         csv_export_received)

    @mock.patch("exports.export_tasks.notify_succeeded.push_email_notification")
    def test_notify_csv_export_succeeded(self, mock_push_notif):
        mock_push_notif.return_value = None
        notify_export_succeeded(failure_reason=None, export_id=self.csv_export.pk)
        mock_push_notif.assert_called()
        self.assertEqual(mock_push_notif.call_args.kwargs["base_notification"],
                         csv_export_succeeded)

    @mock.patch("exports.export_tasks.notify_received.push_email_notification")
    def test_notify_hive_export_received(self, mock_push_notif):
        mock_push_notif.return_value = None
        notify_export_received(export_id=self.hive_export.pk, cohort_id="", cohort_name="")
        mock_push_notif.assert_called()
        self.assertEqual(mock_push_notif.call_args.kwargs["base_notification"],
                         hive_export_received)

    @mock.patch("exports.export_tasks.notify_succeeded.push_email_notification")
    def test_notify_hive_export_succeeded(self, mock_push_notif):
        mock_push_notif.return_value = None
        notify_export_succeeded(failure_reason=None, export_id=self.hive_export.pk)
        mock_push_notif.assert_called()
        self.assertEqual(mock_push_notif.call_args.kwargs["base_notification"],
                         hive_export_succeeded)

    @mock.patch("exports.export_tasks.notify_failed.push_email_notification")
    def test_mark_export_as_failed(self, mock_push_notif: MagicMock):
        mock_push_notif.return_value = None
        mark_export_as_failed(export_id=self.hive_export.pk, failure_reason="some failure reason")
        mock_push_notif.assert_called()
        self.assertEqual(mock_push_notif.call_count, 2)
        self.assertIn(mock_push_notif.call_args.kwargs["base_notification"],
                      [export_failed_notif_for_owner, export_failed_notif_for_admins])
