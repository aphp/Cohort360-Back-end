import logging

from admin_cohort.emails import EmailNotification
from admin_cohort.models import User
from admin_cohort.settings import FRONT_URL, EMAIL_SUPPORT_CONTACT

BASE_CONTEXT = {"contact_email_address": EMAIL_SUPPORT_CONTACT}
_logger = logging.getLogger('info')


def send_email_notif_about_large_cohort(cohort_name: str, cohort_id: str, cohort_owner: User) -> None:
    context = {**BASE_CONTEXT,
               "recipient_name": cohort_owner.displayed_name,
               "cohort_name": cohort_name,
               "cohort_url": f"{FRONT_URL}/cohort/{cohort_id}"
               }
    email_notif = EmailNotification(subject="Votre cohorte est prête",
                                    to=cohort_owner.email,
                                    html_template="large_cohort_finished.html",
                                    txt_template="large_cohort_finished.txt",
                                    context=context)
    email_notif.push()
    _logger.info(f"Email notification sent to user: {cohort_owner}. Cohort [{cohort_name} - {cohort_id}]")


def send_email_notif_about_shared_request(request_name: str, owner: User, recipient: User) -> None:
    subject = f"{owner.firstname} {owner.lastname} a partagé une requête avec vous"
    context = {**BASE_CONTEXT,
               "recipient_name": recipient.displayed_name,
               "owner_name": f"{owner.firstname} {owner.lastname}",
               "request_name": request_name
               }
    email_notif = EmailNotification(subject=subject,
                                    to=recipient.email,
                                    html_template="shared_request.html",
                                    txt_template="shared_request.txt",
                                    context=context)
    email_notif.push()
