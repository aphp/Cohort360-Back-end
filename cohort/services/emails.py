import logging

from admin_cohort.emails import EmailNotification
from admin_cohort.models import User
from admin_cohort.settings import FRONT_URL, EMAIL_SUPPORT_CONTACT, BACK_URL

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
                                    html_template="html/large_cohort_finished.html",
                                    txt_template="txt/large_cohort_finished.txt",
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
                                    html_template="html/shared_request.html",
                                    txt_template="txt/shared_request.txt",
                                    context=context)
    email_notif.push()


def send_email_notif_feasibility_report_confirmed(request_name: str, owner: User) -> None:
    subject = "Votre demande de rapport de faisabilité"
    context = {**BASE_CONTEXT,
               "recipient_name": owner.displayed_name,
               "request_name": request_name
               }
    email_notif = EmailNotification(subject=subject,
                                    to=owner.email,
                                    html_template="html/feasibility_report_requested.html",
                                    txt_template="txt/feasibility_report_requested.txt",
                                    context=context)
    email_notif.push()


def send_email_notif_feasibility_report_ready(request_name: str, owner: User, dm_uuid: str) -> None:
    subject = "Votre rapport de faisabilité est prêt"
    report_link = f"{BACK_URL}/cohort/dated-measures/{dm_uuid}/feasibility"
    context = {**BASE_CONTEXT,
               "recipient_name": owner.displayed_name,
               "request_name": request_name,
               "report_link": report_link
               }
    email_notif = EmailNotification(subject=subject,
                                    to=owner.email,
                                    html_template="html/feasibility_report_ready.html",
                                    txt_template="txt/feasibility_report_ready.txt",
                                    context=context)
    email_notif.push()
