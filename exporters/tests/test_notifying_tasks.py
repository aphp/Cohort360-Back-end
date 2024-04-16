from typing import Callable
from unittest import mock
from unittest.mock import MagicMock

from exporters.notifications import csv_export_received, csv_export_succeeded, hive_export_received, hive_export_succeeded, export_failed
from exporters.tasks import notify_export_received, notify_export_succeeded, notify_export_failed
from exporters.tests.base_test import ExportersTestBase


class TestNotifyingTasks(ExportersTestBase):

    def setUp(self) -> None:
        super().setUp()

    @mock.patch("exporters.tasks.push_email_notification")
    def check_appropriate_notification_was_called(self, task, task_args: dict, base_notification: Callable, mock_push_notif: MagicMock):
        mock_push_notif.return_value = None
        task(**task_args)
        mock_push_notif.assert_called()
        self.assertEqual(mock_push_notif.call_args.kwargs["base_notification"],
                         base_notification)

    def test_notify_csv_export_received(self):
        self.check_appropriate_notification_was_called(notify_export_received,
                                                       dict(export_id=self.csv_export.pk),
                                                       csv_export_received)

    def test_notify_csv_export_succeeded(self):
        self.check_appropriate_notification_was_called(notify_export_succeeded,
                                                       dict(export_id=self.csv_export.pk),
                                                       csv_export_succeeded)

    def test_notify_hive_export_received(self):
        self.check_appropriate_notification_was_called(notify_export_received,
                                                       dict(export_id=self.hive_export.pk),
                                                       hive_export_received)

    def test_notify_hive_export_succeeded(self):
        self.check_appropriate_notification_was_called(notify_export_succeeded,
                                                       dict(export_id=self.hive_export.pk),
                                                       hive_export_succeeded)

    def test_notify_export_failed(self):
        self.check_appropriate_notification_was_called(notify_export_failed,
                                                       dict(export_id=self.hive_export.pk, reason=""),
                                                       export_failed)
