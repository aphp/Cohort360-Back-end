import locale
import logging
import re
from datetime import timedelta
from smtplib import SMTPException
from typing import Tuple

from django.core.mail import EmailMultiAlternatives
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from admin_cohort.settings import EMAIL_BACK_HOST_URL, EMAIL_SENDER_ADDRESS, EMAIL_SUPPORT_CONTACT, \
    DAYS_TO_DELETE_CSV_FILES, EMAIL_REGEX_CHECK
from admin_cohort.types import JobStatus
from .models import ExportRequest
from .types import ExportType

locale.setlocale(locale.LC_ALL, 'fr_FR.utf8')

BACKEND_URL = EMAIL_BACK_HOST_URL
SENDER_EMAIL_ADDR = EMAIL_SENDER_ADDRESS
TEXT_HTML = "text/html"

COHORT360_LOGO = "exports/email_templates/logoCohort360.png"

KEY_DOWNLOAD_URL = "KEY_DOWNLOAD_URL"
KEY_COHORT_ID = "KEY_COHORT_ID"
KEY_NAME = "KEY_NAME"
KEY_ERROR_MESSAGE = "KEY_ERROR_MESSAGE"
KEY_CONTACT_MAIL = "KEY_CONTACT_MAIL"
KEY_CONTENT = "KEY_CONTENT"
KEY_DELETE_DATE = "KEY_DELETE_DATE"
KEY_DATABASE_NAME = "KEY_DATABASE_NAME"
KEY_SELECTED_TABLES = "KEY_SELECTED_TABLES"

_logger = logging.getLogger('django.request')


def send_email(req: ExportRequest, subject, txt_mail, html_mail, to_address):
    msg = EmailMultiAlternatives(subject=subject,
                                 body=replace_keys(txt_mail, req),
                                 from_email=SENDER_EMAIL_ADDR,
                                 to=[to_address])

    msg.attach_alternative(content=replace_keys(html_mail, req, is_html=True),
                           mimetype=TEXT_HTML)
    msg.attach_file(COHORT360_LOGO)
    msg.send()


def get_selected_tables(req: ExportRequest, is_html=False):
    tables = []
    for t in req.tables.all():
        item = is_html and f"<li>{t.omop_table_name}</li>" or f"- {t.omop_table_name}"
        tables.append(item)
    return is_html and f"<ul>{''.join(tables)}</ul>" or "\n".join(tables)


def replace_keys(txt: str, req: ExportRequest, is_html: bool = False) -> str:
    res = txt
    if txt.find(KEY_DOWNLOAD_URL) > -1:
        url = f"{BACKEND_URL}/accounts/login/?next=/exports/{req.id}/download/"
        res = res.replace(KEY_DOWNLOAD_URL,
                          f"<a href='{url}' class=3D'OWAAutoLink'>Télécharger</a>" if is_html else url)

    keys_vals = {KEY_COHORT_ID: req.cohort_id,
                 KEY_NAME: req.creator_fk and req.creator_fk.displayed_name or None,
                 KEY_ERROR_MESSAGE: req.request_job_fail_msg,
                 KEY_CONTACT_MAIL: EMAIL_SUPPORT_CONTACT,
                 KEY_DATABASE_NAME: req.target_name,
                 KEY_DELETE_DATE: (timezone.now().date() +
                                   timedelta(days=int(DAYS_TO_DELETE_CSV_FILES))).strftime("%d %B, %Y"),
                 KEY_SELECTED_TABLES: get_selected_tables(req, is_html=is_html)
                 }
    for k, v in keys_vals.items():
        res = res.replace(str(k), str(v))
    return res


def get_base_templates() -> Tuple[str, str]:
    with open("exports/email_templates/base_template.html") as f:
        html_content = "\n".join(f.readlines())

    with open("exports/email_templates/base_template.txt") as f:
        txt_content = "\n".join(f.readlines())

    return html_content, txt_content


def check_email_address(email: str):
    if not email:
        raise ValidationError("No email address is configured. Please contact an administrator")
    if not re.match(EMAIL_REGEX_CHECK, email):
        raise ValidationError(f"Invalid email address '{email}'. Please contact an administrator.")


def send_failed_email(req: ExportRequest, to_address: str):
    with open("exports/email_templates/resultat_requete_echec.txt") as f:
        txt_content = "\n".join(f.readlines())

    with open("exports/email_templates/resultat_requete_echec.html") as f:
        html_content = "\n".join(f.readlines())

    html_mail, txt_mail = get_base_templates()
    html_mail = html_mail.replace(KEY_CONTENT, html_content)
    txt_mail = txt_mail.replace(KEY_CONTENT, txt_content)

    subject = f"[Cohorte {req.cohort_id}] Votre demande d'export {req.cohort_name or ''} n'a pas abouti"
    send_email(req, subject, txt_mail, html_mail, to_address)


def send_success_email(req: ExportRequest, to_address: str):
    hive_suffix = req.output_format == ExportType.HIVE and '_hive' or ''
    html_path = f"exports/email_templates/resultat_requete_succes{hive_suffix}.html"
    txt_path = f"exports/email_templates/resultat_requete_succes{hive_suffix}.txt"

    with open(html_path) as f:
        html_content = "\n".join(f.readlines())

    with open(txt_path) as f:
        txt_content = "\n".join(f.readlines())

    html_mail, txt_mail = get_base_templates()
    html_mail = html_mail.replace(KEY_CONTENT, html_content)
    txt_mail = txt_mail.replace(KEY_CONTENT, txt_content)
    subject = f"[Cohorte {req.cohort_id}] Export {req.cohort_name or ''} terminé"
    send_email(req, subject, txt_mail, html_mail, to_address)


def email_info_request_done(req: ExportRequest):
    email = req.creator_fk.email
    check_email_address(email)
    try:
        if req.request_job_status == JobStatus.finished:
            send_success_email(req, email)
        elif req.request_job_status in [JobStatus.failed, JobStatus.cancelled]:
            send_failed_email(req, email)
    except (SMTPException, TimeoutError):
        except_msg = f"Could not send export email - request status was '{req.request_job_status}'"
        _logger.exception(f"{except_msg} - Mark it as '{JobStatus.failed}'")
        req.request_job_status = JobStatus.failed
        req.request_job_fail_msg = except_msg
        req.save()
        return
    req.is_user_notified = True
    req.save()


def email_info_request_confirmed(req: ExportRequest, to_address: str):
    hive_suffix = req.output_format == ExportType.HIVE and '_hive' or ''
    html_path = f"exports/email_templates/confirmation_de_requete{hive_suffix}.html"
    txt_path = f"exports/email_templates/confirmation_de_requete{hive_suffix}.txt"

    with open(html_path) as f:
        html_content = "\n".join(f.readlines())

    with open(txt_path) as f:
        txt_content = "\n".join(f.readlines())

    html_mail, txt_mail = get_base_templates()
    html_mail = html_mail.replace(KEY_CONTENT, html_content)
    txt_mail = txt_mail.replace(KEY_CONTENT, txt_content)

    action = f"Demande d'export {req.cohort_name or 'CSV'} reçue"
    if req.output_format == ExportType.HIVE:
        action = "Demande reçue de transfert en environnement Jupyter"
    subject = f"[Cohorte {req.cohort_id}] {action}"
    send_email(req, subject, txt_mail, html_mail, to_address)


def email_info_request_deleted(req: ExportRequest, to_address: str):
    with open("exports/email_templates/confirmation_suppression.html") as f:
        html_content = "\n".join(f.readlines())

    with open("exports/email_templates/confirmation_suppression.txt") as f:
        txt_content = "\n".join(f.readlines())

    html_mail, txt_mail = get_base_templates()
    html_mail = html_mail.replace(KEY_CONTENT, html_content)
    txt_mail = txt_mail.replace(KEY_CONTENT, txt_content)

    subject = f"[Cohorte {req.cohort_id}] Confirmation de suppression de fichier"
    send_email(req, subject, txt_mail, html_mail, to_address)
