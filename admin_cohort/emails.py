import logging
from dataclasses import dataclass
from smtplib import SMTPException
from typing import Optional

from django.core.mail import EmailMultiAlternatives
from django.template.loader import get_template

from admin_cohort.settings import EMAIL_SENDER_ADDRESS

_logger = logging.getLogger('django.request')


@dataclass
class EmailNotification:
    subject: str
    to: str
    html_template: str
    txt_template: str
    context: dict
    html_content: Optional[str] = None
    txt_content: Optional[str] = None

    def build_email_contents(self) -> None:
        self.html_content = get_template(self.html_template).render(self.context)
        self.txt_content = get_template(self.txt_template).render(self.context)

    @staticmethod
    def send_email(email) -> None:
        email.send()

    def push(self) -> None:
        self.build_email_contents()
        email = EmailMultiAlternatives(subject=self.subject,
                                       body=self.txt_content,
                                       from_email=EMAIL_SENDER_ADDRESS,
                                       to=[self.to])
        email.attach_alternative(content=self.html_content, mimetype="text/html")
        email.attach()
        try:
            self.send_email(email)
        except (SMTPException, TimeoutError):
            _logger.exception(f"Error sending export notification. Email Subject was: {self.subject}")
