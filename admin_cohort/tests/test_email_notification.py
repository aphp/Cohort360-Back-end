from smtplib import SMTPException
from unittest import TestCase, mock
from unittest.mock import MagicMock

from admin_cohort.emails import EmailNotification


class EmailNotificationTest(TestCase):

    def setUp(self) -> None:
        super().setUp()
        self.recipient_name = "Some ONE"
        self.context = {"recipient_name": self.recipient_name}
        self.email_notif = self.create_email_notif()

    @mock.patch("admin_cohort.emails.EmailNotification.attach_logo")
    def create_email_notif(self, mock_attach_logo: MagicMock):
        mock_attach_logo.return_value = None
        email_notif = EmailNotification(subject="Email subject",
                                        to="some.one@aphp.fr",
                                        html_template="email_base_template.html",
                                        txt_template="email_base_template.txt",
                                        context=self.context)
        return email_notif

    def test_build_email_contents(self):
        self.email_notif.build_email_contents(context=self.context)
        expected_string_in_content = f"Bonjour {self.recipient_name}"
        self.assertIn(expected_string_in_content, self.email_notif.html_content)
        self.assertIn(expected_string_in_content, self.email_notif.txt_content)

    @mock.patch("admin_cohort.emails.EmailNotification.send")
    @mock.patch("admin_cohort.emails.EmailNotification.attach_logo")
    def test_successfully_push_email_notif(self, mock_attach_logo: MagicMock, mock_send: MagicMock):
        mock_attach_logo.return_value = None
        mock_send.return_value = None
        self.email_notif.push()
        mock_send.assert_called()

    @mock.patch("admin_cohort.emails.EmailNotification.send")
    @mock.patch("admin_cohort.emails.EmailNotification.attach_logo")
    def test_push_email_notif_with_error(self, mock_attach_logo: MagicMock, mock_send: MagicMock):
        mock_attach_logo.return_value = None
        mock_send.side_effect = SMTPException()
        self.email_notif.push()
        mock_send.assert_called()
