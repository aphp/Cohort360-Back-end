from smtplib import SMTPException
from unittest import TestCase, mock
from unittest.mock import MagicMock

from admin_cohort.emails import EmailNotification


class EmailNotificationTest(TestCase):

    def setUp(self) -> None:
        super().setUp()
        self.recipient_name = "Some ONE"
        self.email_notif = EmailNotification(subject="Email subject",
                                             to="some.one@aphp.fr",
                                             html_template="email_base_template.html",
                                             txt_template="email_base_template.txt",
                                             context={"recipient_name": self.recipient_name})

    def test_build_email_contents(self):
        self.email_notif.build_email_contents()
        expected_string_in_content = f"Bonjour {self.recipient_name}"
        self.assertIn(expected_string_in_content, self.email_notif.html_content)
        self.assertIn(expected_string_in_content, self.email_notif.txt_content)

    @mock.patch("admin_cohort.emails.EmailNotification.send_email")
    def test_successfully_push_email_notif(self, mock_email_send: MagicMock):
        mock_email_send.return_value = None
        self.email_notif.push()
        mock_email_send.assert_called()

    @mock.patch("admin_cohort.emails.EmailNotification.send_email")
    def test_push_email_notif_with_error(self, mock_email_send: MagicMock):
        mock_email_send.side_effect = SMTPException()
        self.email_notif.push()
        mock_email_send.assert_called()
