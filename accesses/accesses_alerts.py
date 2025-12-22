import logging
from datetime import date, timedelta

from django.db.models import Max
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
    # Find profiles whose maximum end_datetime among all valid accesses equals the expiry_date.
    # This ensures we only alert users whose latest access is about to expire,
    # not users who have renewed their access (and thus have a later end_datetime).
    profiles_with_max_expiry = Access.objects.filter(accesses_service.q_access_is_valid())\
                                             .values("profile")\
                                             .annotate(max_end_datetime=Max("end_datetime"))\
                                             .filter(max_end_datetime__date=expiry_date)
    for entry in profiles_with_max_expiry:
        profile = Profile.objects.select_related("user").get(pk=entry["profile"])
        if profile.user is None:
            _logger.warning(f"Profile {profile.pk} has no associated user, skipping alert")
            continue
        _logger.info(f"Sending mail to {profile.user} with access expiring in {days}")
        send_alert_email(user=profile.user, days=days)
