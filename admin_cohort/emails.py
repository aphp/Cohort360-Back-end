import logging
from email.mime.image import MIMEImage
from smtplib import SMTPException

from django.core.mail import EmailMultiAlternatives
from django.template.loader import get_template

from admin_cohort.settings import EMAIL_SENDER_ADDRESS, STATIC_ROOT

_logger = logging.getLogger('django.request')


class EmailNotification(EmailMultiAlternatives):
    mixed_subtype = 'related'

    def __init__(self, **kwargs):
        self.html_template = kwargs.pop("html_template", None)
        self.txt_template = kwargs.pop("txt_template", None)
        self.html_content = ""
        self.txt_content = ""
        self.build_email_contents(context=kwargs.pop("context", None))
        kwargs["from_email"] = EMAIL_SENDER_ADDRESS
        kwargs["to"] = [kwargs.pop("to", None)]
        kwargs["body"] = self.txt_content
        super().__init__(**kwargs)
        self.attach_alternative(content=self.html_content, mimetype="text/html")
        self.attach_logo()

    def build_email_contents(self, context: dict) -> None:
        self.html_content = get_template(self.html_template).render(context)
        self.txt_content = get_template(self.txt_template).render(context)

    def attach_logo(self) -> None:
        logo = 'logo_cohort360.png'
        logo_path = STATIC_ROOT/"admin_cohort"/"img"/logo
        with open(logo_path, 'rb') as f:
            img = MIMEImage(f.read())
            img.add_header('Content-ID', f'<{logo}>')
        self.attach(img)

    def push(self) -> None:
        try:
            self.send()
        except (SMTPException, TimeoutError):
            _logger.exception(f"Error sending email notification. Email Subject was: {self.subject}")