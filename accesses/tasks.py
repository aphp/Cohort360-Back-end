from datetime import date, timedelta

from django.core.mail import EmailMultiAlternatives
from django.db.models import Q, Count
from django.utils import timezone

from accesses.models import Access, Profile
from admin_cohort import celery_app
from admin_cohort.models import User
from admin_cohort.settings import ACCESS_EXPIRY_FIRST_ALERT_IN_DAYS, EMAIL_SENDER_ADDRESS, ACCESS_EXPIRY_SECOND_ALERT_IN_DAYS

KEY_NAME = "KEY_NAME"
KEY_EXPIRY_DAYS = "KEY_EXPIRY_DAYS"


def send_alert_email(user: User, in_days: int):
    html_path = "accesses/email_templates/access_expiry_alert.html"
    txt_path = "accesses/email_templates/access_expiry_alert.txt"

    with open(html_path) as f:
        html_content = "\n".join(f.readlines())

    with open(txt_path) as f:
        txt_content = "\n".join(f.readlines())

    html_mail = html_content.replace(KEY_NAME, user.displayed_name).replace(KEY_EXPIRY_DAYS, str(in_days))
    txt_mail = txt_content.replace(KEY_NAME, user.displayed_name).replace(KEY_EXPIRY_DAYS, str(in_days))

    subject = "Expiration de vos accès à Cohort360"
    msg = EmailMultiAlternatives(subject=subject,
                                 body=txt_mail,
                                 from_email=EMAIL_SENDER_ADDRESS,
                                 to=[user.email])

    msg.attach_alternative(content=html_mail, mimetype="text/html")
    msg.attach_file(path="accesses/email_templates/logoCohort360.png")
    msg.send()


def send_access_expiry_alerts(days: int):
    accesses_expiry_date = date.today() + timedelta(days=days)
    expiring_accesses = Access.objects.filter(Q(end_datetime__date=accesses_expiry_date) |
                                              Q(manual_end_datetime__date=accesses_expiry_date))\
                                      .values("profile")\
                                      .annotate(total=Count("profile"))
    for access in expiring_accesses:
        user = Profile.objects.get(pk=access["profile"]).user
        send_alert_email(user=user, in_days=days)


@celery_app.task()
def check_expiring_accesses():
    print("**************************")
    if timezone.now().hour != 9:
        print("************************** not 10h")
        return
    print("************************** 10h")
    send_access_expiry_alerts(days=ACCESS_EXPIRY_FIRST_ALERT_IN_DAYS)
    send_access_expiry_alerts(days=ACCESS_EXPIRY_SECOND_ALERT_IN_DAYS)
