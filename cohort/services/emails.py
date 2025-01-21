import logging

from django.conf import settings

from admin_cohort.emails import EmailNotification
from admin_cohort.models import User


BASE_CONTEXT = {"contact_email_address": settings.EMAIL_SUPPORT_CONTACT}
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


def send_email_notif_feasibility_report_requested(request_name: str, owner: User) -> None:
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
    context = {**BASE_CONTEXT,
               "recipient_name": owner.display_name,
               "request_name": request_name,
               "download_url": f"{settings.FRONT_URL}/download/feasibility-studies/{fs_id}/",
               }
    email_notif = EmailNotification(subject=subject,
                                    to=owner.email,
                                    html_template="html/feasibility_report_ready.html",
                                    txt_template="txt/feasibility_report_ready.txt",
                                    context=context)
    email_notif.push()


def send_email_notif_error_feasibility_report(request_name: str, owner: User) -> None:
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


def send_email_notif_count_request_refreshed(request_name: str, owner: User) -> None:
    subject = "Votre requête a été bien rafraichie"
    context = {**BASE_CONTEXT,
               "recipient_name": owner.display_name,
               "request_name": request_name,
               }
    email_notif = EmailNotification(subject=subject,
                                    to=owner.email,
                                    html_template="html/count_request_refreshed.html",
                                    txt_template="txt/count_request_refreshed.txt",
                                    context=context)
    email_notif.push()
