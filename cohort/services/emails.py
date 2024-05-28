import logging

from admin_cohort.emails import EmailNotification
from admin_cohort.models import User
from admin_cohort.settings import EMAIL_SUPPORT_CONTACT, BACK_URL

BASE_CONTEXT = {"contact_email_address": EMAIL_SUPPORT_CONTACT}
_logger = logging.getLogger('info')


def send_email_notif_about_shared_request(request_name: str, owner: User, recipient: User) -> None:
    subject = f"{owner.firstname} {owner.lastname} a partagé une requête avec vous"
    context = {**BASE_CONTEXT,
               "recipient_name": recipient.display_name,
               "owner_name": f"{owner.firstname} {owner.lastname}",
               "request_name": request_name
               }
    email_notif = EmailNotification(subject=subject,
                                    to=recipient.email,
                                    html_template="html/shared_request.html",
                                    txt_template="txt/shared_request.txt",
                                    context=context)
    email_notif.push()


def send_email_notif_feasibility_report_requested(request_name: str, owner: User, **kwargs) -> None:
    subject = "Votre demande de rapport"
    context = {**BASE_CONTEXT,
               "recipient_name": owner.display_name,
               "request_name": request_name
               }
    email_notif = EmailNotification(subject=subject,
                                    to=owner.email,
                                    html_template="html/feasibility_report_requested.html",
                                    txt_template="txt/feasibility_report_requested.txt",
                                    context=context)
    email_notif.push()


def send_email_notif_feasibility_report_ready(request_name: str, owner: User, fs_id: str) -> None:
    subject = "Votre rapport est prêt"
    report_link = f"{BACK_URL}/auth/login/?next=/cohort/feasibility-studies/{fs_id}/download/"
    context = {**BASE_CONTEXT,
               "recipient_name": owner.display_name,
               "request_name": request_name,
               "report_link": report_link
               }
    email_notif = EmailNotification(subject=subject,
                                    to=owner.email,
                                    html_template="html/feasibility_report_ready.html",
                                    txt_template="txt/feasibility_report_ready.txt",
                                    context=context)
    email_notif.push()


def send_email_notif_error_feasibility_report(request_name: str, owner: User, **kwargs) -> None:
    subject = "Votre demande de rapport a échoué"
    context = {**BASE_CONTEXT,
               "recipient_name": owner.display_name,
               "request_name": request_name,
               }
    email_notif = EmailNotification(subject=subject,
                                    to=owner.email,
                                    html_template="html/feasibility_report_error.html",
                                    txt_template="txt/feasibility_report_error.txt",
                                    context=context)
    email_notif.push()
