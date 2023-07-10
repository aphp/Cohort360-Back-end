import logging
from datetime import date, timedelta

from django.core.mail import EmailMultiAlternatives
from django.db.models import Q, Count

from accesses.models import Access, Profile
from admin_cohort.models import User
from admin_cohort.settings import EMAIL_SENDER_ADDRESS, MANUAL_SOURCE

KEY_NAME = "KEY_NAME"
KEY_EXPIRY_DAYS = "KEY_EXPIRY_DAYS"

_logger = logging.getLogger("info")


def replace_keys(source_text: str, user: User, days: int):
    return source_text.replace(KEY_NAME, user.displayed_name)\
                      .replace(KEY_EXPIRY_DAYS, str(days))


def send_alert_email(user: User, days: int):
    html_path = "accesses/email_templates/access_expiry_alert.html"
    txt_path = "accesses/email_templates/access_expiry_alert.txt"

    with open(html_path) as f:
        html_content = "\n".join(f.readlines())

    with open(txt_path) as f:
        txt_content = "\n".join(f.readlines())

    html_mail = replace_keys(html_content, user, days)
    txt_mail = replace_keys(txt_content, user, days)

    subject = "Expiration de vos accès à Cohort360"
    msg = EmailMultiAlternatives(subject=subject,
                                 body=txt_mail,
                                 from_email=EMAIL_SENDER_ADDRESS,
                                 to=[user.email])

    msg.attach_alternative(content=html_mail, mimetype="text/html")
    msg.attach_file(path="accesses/email_templates/logoCohort360.png")
    msg.send()


def send_access_expiry_alerts(days: int):
    _logger.info("Checking expiring accesses")
    expiry_date = date.today() + timedelta(days=days)
    expiring_accesses = Access.objects.filter(Access.Q_is_valid() &
                                              Q(profile__source=MANUAL_SOURCE) &
                                              (Q(end_datetime__date=expiry_date) |
                                               Q(manual_end_datetime__date=expiry_date)))\
                                      .values("profile")\
                                      .annotate(total=Count("profile"))
    for access in expiring_accesses:
        user = Profile.objects.get(pk=access["profile"]).user
        _logger.info(f"Sending mail to {str(user)} with access expiring in {days}")
        send_alert_email(user=user, days=days)
