import locale
import re
from datetime import timedelta
from typing import Callable

from django.utils import timezone
from rest_framework.exceptions import ValidationError

from admin_cohort.emails import EmailNotification
from admin_cohort.settings import FRONT_URL, EMAIL_SUPPORT_CONTACT, DAYS_TO_KEEP_EXPORTED_FILES, EMAIL_REGEX_CHECK
from exports.enums import ExportType

locale.setlocale(locale.LC_ALL, 'fr_FR.utf8')

BASE_CONTEXT = {"contact_email_address": EMAIL_SUPPORT_CONTACT}


def check_email_address(email: str):
    if not email:
        raise ValidationError("No email address is configured. Please contact an administrator")
    if not re.match(EMAIL_REGEX_CHECK, email):
        raise ValidationError(f"Invalid email address '{email}'. Please contact an administrator.")


def push_email_notification(base_notification: Callable, **kwargs):
    data = base_notification(**kwargs)
    EmailNotification(**data).push()


def export_request_failed(**kwargs):
    subject = f"[Cohorte {kwargs.get('cohort_id')}] Votre demande d'export `{kwargs.get('cohort_name', '')}` n'a pas abouti"
    context = {**BASE_CONTEXT,
               "recipient_name": kwargs.get('recipient_name'),
               "cohort_id": kwargs.get('cohort_id'),
               "error_message": kwargs.get('error_message')
               }
    return dict(subject=subject,
                to=kwargs.get('recipient_email'),
                html_template="html/resultat_requete_echec.html",
                txt_template="txt/resultat_requete_echec.txt",
                context=context)


def export_request_succeeded(**kwargs):
    subject = f"[Cohorte {kwargs.get('cohort_id')}] Export `{kwargs.get('cohort_name', '')}` terminé"
    context = {**BASE_CONTEXT,
               "recipient_name": kwargs.get('recipient_name'),
               "cohort_id": kwargs.get('cohort_id'),
               "selected_tables": kwargs.get('selected_tables'),
               "download_url": f"{FRONT_URL}/exports/{kwargs.get('export_request_id')}/download/",
               "database_name": kwargs.get('database_name'),
               "delete_date": (timezone.now().date() + timedelta(days=DAYS_TO_KEEP_EXPORTED_FILES)).strftime("%d %B %Y")
               }
    return dict(subject=subject,
                to=kwargs.get('recipient_email'),
                html_template=f"html/resultat_requete_succes_{kwargs.get('output_format')}.html",
                txt_template=f"txt/resultat_requete_succes_{kwargs.get('output_format')}.txt",
                context=context)


def export_request_received(**kwargs):
    action = f"Demande d'export `{kwargs.get('cohort_name', 'CSV')}` reçue"
    if kwargs.get('output_format') == ExportType.HIVE:
        action = "Demande reçue de transfert en environnement Jupyter"
    context = {**BASE_CONTEXT,
               "recipient_name": kwargs.get('recipient_name'),
               "cohort_id": kwargs.get('cohort_id'),
               "selected_tables": kwargs.get('selected_tables')
               }
    return dict(subject=f"[Cohorte {kwargs.get('cohort_id')}] {action}",
                to=kwargs.get('recipient_email'),
                html_template=f"html/confirmation_de_requete_{kwargs.get('output_format')}.html",
                txt_template=f"txt/confirmation_de_requete_{kwargs.get('output_format')}.txt",
                context=context)


def exported_csv_files_deleted(**kwargs):
    context = {'recipient_name': kwargs.get('recipient_name'),
               'cohort_id': kwargs.get('cohort_id')
               }
    return dict(subject=f"[Cohorte {kwargs.get('cohort_id')}] Confirmation de suppression de fichiers CSV exportés",
                to=kwargs.get('recipient_email'),
                html_template="html/confirmation_suppression_csv.html",
                txt_template="txt/confirmation_suppression_csv.txt",
                context=context)
