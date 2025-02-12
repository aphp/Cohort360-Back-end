import logging
from datetime import date, timedelta

from django.db.models import Q, Count
from django.conf import settings

from accesses.models import Access, Profile
from accesses.services.accesses import accesses_service
from admin_cohort.emails import EmailNotification
from admin_cohort.models import User

_logger = logging.getLogger("info")

MANUAL = settings.ACCESS_SOURCES[0]


def send_alert_email(user: User, days: int):
    context = {"recipient_name": user.display_name,
               "expiry_days": days,
               "access_managers_list_link": settings.ACCESS_MANAGERS_LIST_LINK
               }
    email_notif = EmailNotification(subject="Expiration de vos accès à Cohort360",
                                    to=[user.email],
                                    html_template="access_expiry_alert.html",
                                    txt_template="access_expiry_alert.txt",
                                    context=context)
    email_notif.push()


def send_access_expiry_alerts(days: int):
    _logger.info("Checking expiring accesses")
    expiry_date = date.today() + timedelta(days=days)
    expiring_accesses = Access.objects.filter(accesses_service.q_access_is_valid() &
                                              Q(end_datetime__date=expiry_date))\
                                      .values("profile")\
                                      .annotate(total=Count("profile"))
    for access in expiring_accesses:
        user = Profile.objects.get(pk=access["profile"]).user
        _logger.info(f"Sending mail to {str(user)} with access expiring in {days}")
        send_alert_email(user=user, days=days)
