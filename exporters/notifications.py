from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from exporters.enums import ExportTypes

CSV = ExportTypes.CSV.value
HIVE = ExportTypes.HIVE.value
XLSX = ExportTypes.XLSX.value

BASE_CONTEXT = {"contact_email_address": settings.EMAIL_SUPPORT_CONTACT}


def export_received(action: str, export_type: str, **kwargs):
    context = {**BASE_CONTEXT,
               "recipient_name": kwargs.get('recipient_name'),
               "cohort_id": kwargs.get('cohort_id'),
               "selected_tables": kwargs.get('selected_tables')
               }
    return dict(subject=f"[Cohorte {kwargs.get('cohort_id')}] {action}",
                to=kwargs.get('recipient_email'),
                html_template=f"html/{export_type}_export_received.html",
                txt_template=f"txt/{export_type}_export_received.txt",
                context=context)


def export_succeeded(export_type: str, **kwargs):
    subject = f"[Cohorte {kwargs.get('cohort_id')}] Export `{kwargs.get('cohort_name', '')}` terminé"
    context = {**BASE_CONTEXT,
               "recipient_name": kwargs.get('recipient_name'),
               "cohort_id": kwargs.get('cohort_id'),
               "selected_tables": kwargs.get('selected_tables'),
               "download_url": f"{settings.FRONT_URL}/download/exports/{kwargs.get('export_request_id')}/",
               "database_name": kwargs.get('database_name'),
               "delete_date": (timezone.now().date() + timedelta(days=settings.DAYS_TO_KEEP_EXPORTED_FILES)).strftime("%d %B %Y")
               }
    return dict(subject=subject,
                to=kwargs.get('recipient_email'),
                html_template=f"html/{export_type}_export_succeeded.html",
                txt_template=f"txt/{export_type}_export_succeeded.txt",
                context=context)


def export_failed(**kwargs):
    subject = f"[Cohorte {kwargs.get('cohort_id')}] Votre demande d'export `{kwargs.get('cohort_name', '')}` n'a pas abouti"
    context = {**BASE_CONTEXT,
               "recipient_name": kwargs.get('recipient_name'),
               "cohort_id": kwargs.get('cohort_id'),
               "error_message": kwargs.get('error_message')
               }
    return dict(subject=subject,
                to=kwargs.get('recipient_email'),
                html_template="html/export_failed.html",
                txt_template="txt/export_failed.txt",
                context=context)


def csv_export_received(**kwargs):
    return export_received(action=f"Demande d'export `{kwargs.get('cohort_name', CSV)}` reçue",
                           export_type=CSV,
                           **kwargs)


def hive_export_received(**kwargs):
    return export_received(action="Demande reçue de transfert en environnement Jupyter",
                           export_type=HIVE,
                           **kwargs)


def csv_export_succeeded(**kwargs):
    return export_succeeded(export_type=CSV, **kwargs)


def hive_export_succeeded(**kwargs):
    return export_succeeded(export_type=HIVE, **kwargs)


EXPORT_RECEIVED_NOTIFICATIONS = {CSV: csv_export_received,
                                 HIVE: hive_export_received,
                                 XLSX: csv_export_received     # XLSX and CSV use the same email template
                                 }

EXPORT_SUCCEEDED_NOTIFICATIONS = {CSV: csv_export_succeeded,
                                  HIVE: hive_export_succeeded,
                                  XLSX: csv_export_succeeded     # XLSX and CSV use the same email template
                                  }
