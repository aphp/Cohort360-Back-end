from smtplib import SMTPException
from unittest import mock
from unittest.mock import MagicMock

from admin_cohort.emails import EmailNotification
from admin_cohort.tests.tests_tools import TestCaseWithDBs


class EmailNotificationTest(TestCaseWithDBs):

    def setUp(self) -> None:
        super().setUp()
        self.recipient_name = "Some ONE"
        self.context = {"recipient_name": self.recipient_name}
        self.email_notif = self.create_email_notif()

    @mock.patch("admin_cohort.emails.EmailNotification.build_email_contents")
    @mock.patch("admin_cohort.emails.EmailNotification.attach_logo")
    def create_email_notif(self, mock_attach_logo: MagicMock, mock_build_email_contents: MagicMock):
        mock_attach_logo.return_value = None
        mock_build_email_contents.return_value = None
        email_notif = EmailNotification(subject="Email subject",
                                        to=["some.one@aphp.fr"],
                                        html_template='',
                                        txt_template='',
                                        context=self.context)
        return email_notif

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
