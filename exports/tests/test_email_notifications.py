from unittest import TestCase, mock
from unittest.mock import MagicMock

from exports.emails import export_request_failed, export_request_succeeded, export_request_received, exported_csv_files_deleted, \
    push_email_notification


class EmailNotificationsTests(TestCase):

    def setUp(self) -> None:
        super().setUp()
        self.notif_data = dict(recipient_name="Some USER",
                               recipient_email="some.user@aphp.fr",
                               cohort_id="cohort_id",
                               cohort_name="cohort_name",
                               export_request_id="export_request_id",
                               output_format="csv",
                               database_name="database_name",
                               selected_tables="table01,table02",
                               error_message="error_message")
        self.registered_notifications = [export_request_failed,
                                         export_request_succeeded,
                                         export_request_received,
                                         exported_csv_files_deleted
                                         ]

    @mock.patch("exports.emails.EmailNotification.push")
    @mock.patch("exports.emails.EmailNotification.attach_logo")
    def test_push_email_notification(self, mock_attach_logo: MagicMock, mock_notif_push: MagicMock):
        mock_attach_logo.return_value = None
        mock_notif_push.return_value = None
        for notif in self.registered_notifications:
            push_email_notification(notif, **self.notif_data)
            mock_notif_push.assert_called()
