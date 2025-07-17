import re
from typing import Callable

from django.conf import settings
from rest_framework.exceptions import ValidationError

from admin_cohort.emails import EmailNotification


def check_email_address(email: str):
    if not email:
        raise ValidationError("No email address is configured. Please contact an administrator")
    if not re.match(settings.EMAIL_REGEX, email):
        raise ValidationError(f"Invalid email address '{email}'. Please contact an administrator.")


def push_email_notification(base_notification: Callable, **kwargs):
    data = base_notification(**kwargs)
    EmailNotification(**data).push()


def exported_files_deleted(**kwargs):
    context = {'recipient_name': kwargs.get('recipient_name'),
               'cohort_id': kwargs.get('cohort_id')
               }
    return {"subject": f"[Cohorte {kwargs.get('cohort_id')}] Confirmation de suppression de fichiers exportés",
            "to": [kwargs.get('recipient_email')],
            "html_template": "exported_files_deleted.html",
            "txt_template": "exported_files_deleted.txt",
            "context": context
            }
