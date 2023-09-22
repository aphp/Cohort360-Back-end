import locale
import re
from datetime import timedelta
from typing import Callable

from django.utils import timezone
from rest_framework.exceptions import ValidationError

from admin_cohort.emails import EmailNotification
from admin_cohort.settings import EMAIL_BACK_HOST_URL, EMAIL_SUPPORT_CONTACT, DAYS_TO_DELETE_CSV_FILES, EMAIL_REGEX_CHECK
from .models import ExportRequest
from .types import ExportType

locale.setlocale(locale.LC_ALL, 'fr_FR.utf8')

BACKEND_URL = EMAIL_BACK_HOST_URL
BASE_CONTEXT = {"contact_email_address": EMAIL_SUPPORT_CONTACT}


def check_email_address(email: str):
    if not email:
        raise ValidationError("No email address is configured. Please contact an administrator")
    if not re.match(EMAIL_REGEX_CHECK, email):
        raise ValidationError(f"Invalid email address '{email}'. Please contact an administrator.")


def push_email_notification(notification: Callable[[ExportRequest], None], export_request):
    notification(export_request)


def send_failure_email(export_request: ExportRequest):
    subject = f"[Cohorte {export_request.cohort_id}] Votre demande d'export `{export_request.cohort_name or ''}` n'a pas abouti"
    context = {**BASE_CONTEXT,
               "recipient_name": export_request.owner.displayed_name,
               "cohort_id": export_request.cohort_id,
               "error_message": export_request.request_job_fail_msg
               }
    email_notif = EmailNotification(subject=subject,
                                    to=export_request.owner.email,
                                    html_template="resultat_requete_echec.html",
                                    txt_template="resultat_requete_echec.txt",
                                    context=context)
    email_notif.push()


def send_success_email(export_request: ExportRequest):
    subject = f"[Cohorte {export_request.cohort_id}] Export `{export_request.cohort_name or ''}` terminé"
    context = {**BASE_CONTEXT,
               "recipient_name": export_request.owner.displayed_name,
               "cohort_id": export_request.cohort_id,
               "selected_tables": export_request.tables.values_list("omop_table_name", flat=True),
               "download_url": f"{BACKEND_URL}/accounts/login/?next=/exports/{export_request.id}/download/",
               "database_name": export_request.target_name,
               "delete_date": (timezone.now().date() + timedelta(days=int(DAYS_TO_DELETE_CSV_FILES))).strftime("%d %B %Y")
               }
    email_notif = EmailNotification(subject=subject,
                                    to=export_request.owner.email,
                                    html_template=f"resultat_requete_succes_{export_request.output_format}.html",
                                    txt_template=f"resultat_requete_succes_{export_request.output_format}.txt",
                                    context=context)
    email_notif.push()


def email_info_request_received(export_request: ExportRequest):
    action = f"Demande d'export `{export_request.cohort_name or 'CSV'}` reçue"
    if export_request.output_format == ExportType.HIVE:
        action = "Demande reçue de transfert en environnement Jupyter"
    subject = f"[Cohorte {export_request.cohort_id}] {action}"
    context = {**BASE_CONTEXT,
               "recipient_name": export_request.owner.displayed_name,
               "cohort_id": export_request.cohort_id,
               "selected_tables": export_request.tables.values_list("omop_table_name", flat=True)
               }
    email_notif = EmailNotification(subject=subject,
                                    to=export_request.owner.email,
                                    html_template=f"confirmation_de_requete_{export_request.output_format}.html",
                                    txt_template=f"confirmation_de_requete_{export_request.output_format}.txt",
                                    context=context)
    email_notif.push()


def email_info_csv_files_deleted(export_request: ExportRequest):
    subject = f"[Cohorte {export_request.cohort_id}] Confirmation de suppression de fichiers"
    context = {'recipient_name': export_request.owner.displayed_name}
    email_notif = EmailNotification(subject=subject,
                                    to=export_request.owner.email,
                                    html_template="confirmation_suppression_csv.html",
                                    txt_template="confirmation_suppression_csv.txt",
                                    context=context)
    email_notif.push()
